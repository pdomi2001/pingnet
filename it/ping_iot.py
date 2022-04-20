# ping-iot revisited

from threading import Thread
import subprocess
try:from Queue import Queue
except:from queue import Queue
import time
import sys
import logging
import argparse
import configparser
import sqlite3
parser=argparse.ArgumentParser()

start_init=time.perf_counter()


parser.add_argument("-l","--logfile",default=None,
                    help='aggiunge un handler del file sul log.')
parser.add_argument("-tn","--threads-number",type=int,default=100,
                    help='il numero di thread usati nella queue.')
parser.add_argument("-c", "--configuration", type=str,
                    help='configurazione di ping.',default='DEFAULT')
parser.add_argument("-r","--repeat",action="store_true",
                    help='abilita la ripetizione di controllo')
parser.add_argument("-p", "--pausa", type=float,default=5,
                    help="pausa da uno scan all'altro.")
parser.add_argument("-nt", "--no-typology", action="store_true",
                    help='rimuove la topologia degli scan.')
parser.add_argument("-w","--webmode",action="store_true",
                    help='produce un file web risultante.')
parser.add_argument("-v","--verbose",action="store_true",
                    help="abilita la verbosità dell'output")
parser.add_argument("-ts","--save-time-dataframe",action="store_true",
                    default=False,help="salva il dataframe del tempo in un file (csv,html e xmls).")
args=parser.parse_args()
level = 20-10*args.verbose
logging.basicConfig(format='%(asctime)s\\%(levelname)s:%(message)s',
                    datefmt='%H:%M:%S',level=level)
logger=logging.getLogger(__name__)
if args.logfile:
  #add a file handler
  fh=logging.FileHandler(' '.join(args.logfile))
  fh.setLevel(level)
  formatter=logging.Formatter('%(asctime)s\\%(levelname)s:%(message)s')
  fh.setFormatter(formatter)
  logger.addHandler(fh)
repeat=args.repeat
show_typology=not args.no_typology
webmode=args.webmode
pausa=args.pausa
num_threads=args.threads_number
st=args.save_time_dataframe
#configurazione di ping

config=configparser.ConfigParser()
config.read('config.ini')

if not args.configuration=='DEFAULT':config_section=config[args.configuration]
else:config_section=config.defaults()
logger.debug("settando configurazione di ping a %s"%'\n'.join(map(lambda x:f"{x[0]}: {x[1]}",config_section.items())))

class tipo_controllo():
  Nessuno = 0
  Sempre_acceso = 1
  Spegnere_prima_di_uscire = 2

def _getnum(items):
  item=items[0].split(".")[2]
  if item=='from':return 0
  elif item=='to':return 1
  elif item=='name':return 2
  elif item=='tipo':return 3
  else:return 4

def gnt(string):
  return int(string.split(".")[1])

def splitby(items:list[tuple[str,str]]):
  final={}
  for key,val in items:
    if key.split(".")[1] not in final:
      if final.get(int(key.split(".")[1])):
        final[int(key.split(".")[1])].append(val)
      else:
        final[int(key.split(".")[1])]=[val]
  final=list(map(lambda lst:[*map(int,(lst[0],lst[1])),lst[2],tipo_controllo().__getattribute__(lst[3])],list(final.values())))
  return final
p_reti=dict([x for x in config_section.items() if x[0].startswith('reti.')])
p_reti=dict(sorted(p_reti.items(),key=_getnum))
# p_reti=[rete for rete in sorted(p_reti.items(),key=_getnum)]

# p_reti2=dict([x for x in config_section.items() if x[0].startswith('reti2.')])
# p_reti2=dict(sorted(p_reti2.items(),key=_getnum))

reti=splitby(list(p_reti.items())[:-1])
# reti2=splitby(list(p_reti2.items())[:-1])

string_base_ip=list(p_reti.values())[-1]
# string_base_ip2=list(p_reti2.values())[-1]

# num_pcs=sum(list(map(lambda x:x[1],reti)))+sum(list(map(lambda x:x[1],reti2)))
num_pcs=sum(list(map(lambda x:x[1],reti)))

addresses,desc_pc,scan_results,pc_type = [],[],[],[]

for idx in range(num_pcs):
  addresses.append(idx)
  desc_pc.append(idx)
  scan_results.append(idx)
  pc_type.append(idx)

num_pc = 0
results = {}

# for singolarete in [[reti, string_base_ip], [reti2, string_base_ip2]]:
#   for rete in singolarete[0]: #reti:
#     for index in range(rete[1]):
#       #a = "%s%d"% (string_base_ip, rete[0] + index)
#       addresses[num_pc] = "{}{}".format(singolarete[1], rete[0] + index)
#       if rete[1] == 1:
#         desc_pc[num_pc] = rete[2]
#       else:
#         desc_pc[num_pc] = "{} {}".format(rete[2], index+1)
#       pc_type[num_pc] = rete[3]
#       num_pc+=1
for rete in reti:
  for index in range(rete[1]):
    #a = "%s%d"% (string_base_ip, rete[0] + index)
    addresses[num_pc] = "{}{}".format(string_base_ip, rete[0] + index)
    if rete[1] == 1:
      desc_pc[num_pc] = rete[2]
    else:
      desc_pc[num_pc] = "{} {}".format(rete[2], index+1)
    pc_type[num_pc] = rete[3]
    num_pc+=1

queue = Queue()

#wraps system ping command
if sys.platform=='win32':
  def pinger(i, q):
    """Pings subnet"""
    while 1:
      idx = q.get()
      ip = addresses[idx]
      logger.debug("Thread {}: Pinging {}".format(i, ip))
      ret = subprocess.call(f"ping -n 1 -w 500 -l 1 {ip}",
        shell=True,
        stdout=open('NUL', 'w'),
        stderr=subprocess.STDOUT)
      if not ret:
        logger.debug("{}: is alive".format(ip))
        scan_results[idx] = "acceso"
      else:
        logger.debug("{}: did not respond".format(ip))
        scan_results[idx] = "spento"
      q.task_done()
else:
  def pinger(i, q):
    """Pings subnet"""
    while 1:
      idx = q.get()
      ip = addresses[idx]
      logger.debug("Thread {}: Pinging {}".format(i, ip))
      ret = subprocess.call(f"ping -c 1 {ip}",
        shell=True,
        stdout=open('/dev/null', 'w'),
        stderr=subprocess.STDOUT)
      if ret == 0:
          logger.debug("{}: is alive".format(ip))
          scan_results[idx] = "acceso"
      else:
          logger.debug("{}: did not respond".format(ip))
          scan_results[idx] = "spento"
      q.task_done()

end_init=time.perf_counter()
logger.debug("finita inizializzazione in %f secondi"%(end_init-start_init))

logger.debug("creazione thread")
for i in range(num_threads):
  worker = Thread(target=pinger, args=(i, queue))
  worker.daemon = True
  worker.start()
logger.debug("thread creati")

while 1:
  
    logger.info("Inizio controllo")
    start_controllo=time.perf_counter()

    for idx in range(num_pcs):
      queue.put(idx)
    queue.join()

    end_controllo=time.perf_counter()
    logger.debug("controllo finito.")
    logger.debug("Inizio visualizzazione.")
    start_visualizzazione=time.perf_counter()

    if not webmode:
      logger.debug("Vedendo risultato..")
      accesi = scan_results.count("acceso")
      for addr,desc,res in zip(addresses,desc_pc,scan_results):
        if res == "acceso":
          logger.info(f" {addr} {desc} {res}")
      logger.info(f"PC Accesi :{accesi}/{num_pcs}\n")
      # per tutti i raggruppamenti di reti
      
      for rete in reti: 
        stringa = "{}{}:{} =>".format(string_base_ip, rete[0], rete[2])
        for index in range(rete[1]):
          a = "".join(map(str,(string_base_ip, rete[0]+index)))
          idx = addresses.index(a)
          stringa += ' X' if scan_results[idx] == "acceso" else ' .'
        logger.info("mapping della rete:{}".format(stringa))
    if show_typology:
      # controllo in base alla tipologia
      logger.info("Controllo in base alla tipologia")
      for scan_res,typ,addr,pc_desc in zip(scan_results,pc_type,addresses,desc_pc):
        if scan_res != "acceso" and typ == tipo_controllo.Sempre_acceso:
          logging.info(' '.join(("*** Attenzione Spento *** =>",addr, pc_desc, scan_res)))
      for scan_res,typ,addr,pc_desc in zip(scan_results,pc_type,addresses,desc_pc):
        if (scan_res == "acceso" and typ == tipo_controllo.Spegnere_prima_di_uscire):
          logging.info(' '.join(("--- Spegnere prima di chiudere --- =>",addr,pc_desc,scan_res)))
    if webmode:
        logger.debug("stampa web")
        refreshtime = pausa if pausa>0 else 30
        webpage = [f'<html><head><meta http-equiv="refresh" content="{refreshtime}"></head><body>',"Last update: {} del {}".format(time.strftime("%H:%M:%S"), time.strftime("%d/%m/%Y")),"<table border=1 width=100%>"]
        # per tutti i raggruppamenti di reti
        for rete in reti:
          num_pc_in_gruppo = 1
          stringaweb ="<tr><td>{}{}</td><td>{}</td>".format(string_base_ip, rete[0], rete[2])
          stringa = "{}{}:{} =>".format(string_base_ip, rete[0], rete[2])
          stringaweb2 = ""
          for index in range(rete[1]):
            a = ''.join(map(str,(string_base_ip, rete[0]+index)))
            idx = addresses.index(a)
            coloretesto = "black"
            # if (pc_type[idx] == tipo_controllo.Sempre_acceso):
            if pc_type[idx] == 1:
                if scan_results[idx] == "acceso":
                  coloresfondo,coloretesto = "blue","white"
                else:
                  coloresfondo = "red" 
                  stringa += ' X'
            else:
                if scan_results[idx] == "acceso":coloresfondo = "lightgreen"
                else:coloresfondo = "yellow"
            stringa += ' .'
            stringaweb2 = ('%s<td style="background: %s; color: %s; width: 25px;">%d</td>' % (stringaweb2, coloresfondo, coloretesto, num_pc_in_gruppo))
            num_pc_in_gruppo += 1
          webpage.extend([stringaweb,stringaweb2,"<tr>"])
        webpage.append("</table></body></html>")
        with open("netstatus.html","w") as out_file:
          out_file.write("".join(webpage))
    end_visualizzazione = time.perf_counter()
    if not repeat:break
    if not webmode:
        logging.info("Aspetto %.2f secondi" % pausa)
        time.sleep(pausa)
end=time.perf_counter()
import pandas as pd
import os
# creo il dataframe dei tempi
logger.debug("generazione dataframe")
tempi = pd.DataFrame({"totale":[end-start_init],"inizializzazione":[end_init-start_init],"controllo":[end_controllo-start_controllo],"visualizzazione":[end_visualizzazione-start_visualizzazione]})
logger.debug("acquisizione directory")
def getfilepath(filename):
  return os.path.abspath(os.path.join(config_section.get("tempi.path"),filename))

if st:
  logger.info("mettendo i tempi su diversi file")
  logger.debug("metto i tempi su csv")
  try:
    csv_path=getfilepath("tempi.csv")
    if not os.path.exists(csv_path):
      tempi.to_csv(csv_path,index=False)
    else:
      df=pd.read_csv(csv_path)
      df=pd.concat([df,tempi])
      df.to_csv(csv_path,index=False)
    logger.debug("metto i tempi su html")
    html_path=getfilepath("tempi.html")
    if not os.path.exists(html_path):
      tempi.to_html(html_path,index=False)
    else:
      df=pd.read_html(html_path)
      df.append(tempi)
      df=pd.concat(df)
      df.to_html(html_path,index=False)
    logger.debug("metto i tempi su excel")
    excel_path=getfilepath("tempi.xlsx")
    if not os.path.exists(excel_path):
      tempi.to_excel(excel_path,index=False)
    else:
      df=pd.read_excel(excel_path)
      df=pd.concat([df,tempi])
      df.to_excel(excel_path,index=False)
  except Exception as e:
    logger.error("errore durante la scrittura dei tempi")
    logger.error(e)
  logger.info("tempi scritti")
logger.info("Fine")
