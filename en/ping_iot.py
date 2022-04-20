# ping-iot revisited

from threading import Thread
import subprocess
from queue import Queue
import time
import sys
import logging
import argparse
import configparser
parser=argparse.ArgumentParser()

start_init=time.perf_counter()


parser.add_argument("-l","--logfile",default=None,
                    help='adds an handler on the logger.')
parser.add_argument("-tn","--threads-number",type=int,default=100,
                    help='il numero di thread usati nella queue.')
parser.add_argument("-c", "--configuration", type=str,
                    help='ping configuration.',default='DEFAULT')
parser.add_argument("-r","--repeat",action="store_true",
                    help='repeats the control infinitely many times')
parser.add_argument("-p", "--pause", type=float,default=5,
                    help="scan delay.")
parser.add_argument("-nt", "--no-topography", action="store_true",
                    help='removes scan topology.')
parser.add_argument("-w","--webmode",action="store_true",
                    help='produces an html file')
parser.add_argument("-v","--verbose",action="store_true",
                    help="verbose output.")
parser.add_argument("-ts","--save-time-dataframe",action="store_true",
                    default=False,help="saves dataframe of execution times(csv,html e xmls).")
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
show_topography=not args.no_topography
webmode=args.webmode
pausa=args.pause
num_threads=args.threads_number
st=args.save_time_dataframe
#ping configuration

config=configparser.ConfigParser()
config.read('config.ini')

if not args.configuration=='DEFAULT':config_section=config[args.configuration]
else:config_section=config.defaults()
logger.debug("setting ping configuration %s"%'\n'.join(map(lambda x:f"{x[0]}: {x[1]}",config_section.items())))

class control_type():
  _None = 0
  Always_active = 1
  to_switch_off = 2

def _getnum(items):
  item=items[0].split(".")[2]
  if item=='from':return 0
  elif item=='to':return 1
  elif item=='name':return 2
  elif item=='type':return 3
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
  final=list(map(lambda lst:[*map(int,(lst[0],lst[1])),lst[2],control_type().__getattribute__(lst[3])],list(final.values())))
  return final
p_reti=dict([x for x in config_section.items() if x[0].startswith('networks.')])
p_reti=dict(sorted(p_reti.items(),key=_getnum))

networks=splitby(list(p_reti.items())[:-1])

ipv4base=list(p_reti.values())[-1]
num_pcs=sum(list(map(lambda x:x[1],networks)))

addresses,desc_pc,scan_results,pc_type = [],[],[],[]

for idx in range(num_pcs):
  addresses.append(idx)
  desc_pc.append(idx)
  scan_results.append(idx)
  pc_type.append(idx)

num_pc = 0
results = {}

for network in networks:
  for index in range(network[1]):
    #a = "%s%d"% (string_base_ip, rete[0] + index)
    addresses[num_pc] = "{}{}".format(ipv4base, network[0] + index)
    if network[1] == 1:
      desc_pc[num_pc] = network[2]
    else:
      desc_pc[num_pc] = "{} {}".format(network[2], index+1)
    pc_type[num_pc] = network[3]
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
        scan_results[idx] = "on"
      else:
        logger.debug("{}: did not respond".format(ip))
        scan_results[idx] = "off"
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
          scan_results[idx] = "on"
      else:
          logger.debug("{}: did not respond".format(ip))
          scan_results[idx] = "off"
      q.task_done()

end_init=time.perf_counter()
logger.debug("inizializzation ended in %f second(s)"%(end_init-start_init))

logger.debug("creating thread")
for i in range(num_threads):
  worker = Thread(target=pinger, args=(i, queue))
  worker.daemon = True
  worker.start()
logger.debug("threads created")

while 1:

    logger.info("Start performing check")
    start_controllo=time.perf_counter()

    for idx in range(num_pcs):
      queue.put(idx)
    queue.join()

    end_controllo=time.perf_counter()
    logger.debug("check ended.")
    logger.debug("Starting visualization.")
    start_visualization=time.perf_counter()

    if not webmode:
      logger.debug("Visualizing result..")
      accesi = scan_results.count("acceso")
      for addr,desc,res in zip(addresses,desc_pc,scan_results):
        if res == "acceso":
          logger.info(f" {addr} {desc} {res}")
      logger.info(f"Open PCs :{accesi}/{num_pcs}\n")
      # per tutti i raggruppamenti di reti

      for network in networks:
        _str = "{}{}:{} =>".format(ipv4base, network[0], network[2])
        for index in range(network[1]):
          a = "".join(map(str,(ipv4base, network[0]+index)))
          idx = addresses.index(a)
          _str += ' X' if scan_results[idx] == "acceso" else ' .'
        logger.info("topography:{}".format(_str))
    if show_topography:
      # controllo in base alla tipologia
      logger.info("Visualizing tipology of PCs..")
      for scan_res,typ,addr,pc_desc in zip(scan_results,pc_type,addresses,desc_pc):
        if scan_res != "on" and typ == control_type.Always_active:
          logging.info(' '.join(("*** WARNING:DEVICE IS OFF *** =>",addr, pc_desc, scan_res)))
      for scan_res,typ,addr,pc_desc in zip(scan_results,pc_type,addresses,desc_pc):
        if (scan_res == "on" and typ == control_type.to_switch_off):
          logging.info(' '.join(("--- TURN OFF BEFORE LEAVING --- =>",addr,pc_desc,scan_res)))
    if webmode:
        logger.warning("webmode is on, visualization will be skipped.")
        logger.debug("building webfile.")
        refreshtime = pausa if pausa>0 else 30
        webpage = [f'<html><head><meta http-equiv="refresh" content="{refreshtime}"></head><body>',"Last update: {} del {}".format(time.strftime("%H:%M:%S"), time.strftime("%d/%m/%Y")),"<table border=1 width=100%>"]
        
        for network in networks:
          num_group_pcs = 1
          webstr ="<tr><td>{}{}</td><td>{}</td>".format(ipv4base, network[0], network[2])
          _str = "{}{}:{} =>".format(ipv4base, network[0], network[2])
          webstr2 = ""
          for index in range(network[1]):
            a = ''.join(map(str,(ipv4base, network[0]+index)))
            idx = addresses.index(a)
            colour = "black"
            # if (pc_type[idx] == tipo_controllo.Sempre_acceso):
            if pc_type[idx] == 1:
                if scan_results[idx] == "on":
                  backgroundcolour,colour = "blue","white"
                else:
                  backgroundcolour = "red"
                  _str += ' X'
            else:
                if scan_results[idx] == "on":backgroundcolour = "lightgreen"
                else:backgroundcolour = "yellow"
            _str += ' .'
            webstr2 = ('%s<td style="background: %s; color: %s; width: 25px;">%d</td>' % (webstr2, backgroundcolour, colour, num_group_pcs))
            num_group_pcs += 1
          webpage.extend([webstr,webstr2,"<tr>"])
        webpage.append("</table></body></html>")
        with open("netstatus.html","w") as out_file:
          out_file.write("".join(webpage))
    end_visualizzazione = time.perf_counter()
    if not repeat:break
    if not webmode:
      logging.info("Waiting %.2f secondi" % pausa)
      time.sleep(pausa)
end=time.perf_counter()
# creating times dataframe
if st:
  import pandas as pd
  import os

  logger.debug("creating dataframe")
  times = pd.DataFrame({"totale":[end-start_init],"inizializzazione":[end_init-start_init],"controllo":[end_controllo-start_controllo],"visualizzazione":[end_visualizzazione-start_visualization]})
  logger.debug(f"{times=!r}")
  logger.debug("getting current directory")
  def getfilepath(filename):
    return os.path.abspath(os.path.join(config_section.get("times.path"),filename))
  logger.info("exporting dataframe...")
  logger.debug("saving dataframe to csv")
  try:
    csv_path=getfilepath("times.csv")
    if not os.path.exists(csv_path):
      times.to_csv(csv_path,index=False)
    else:
      df=pd.read_csv(csv_path)
      df=pd.concat([df,times])
      df.to_csv(csv_path,index=False)
    logger.debug("saving dataframe to html")
    html_path=getfilepath("times.html")
    if not os.path.exists(html_path):
      times.to_html(html_path,index=False)
    else:
      df=pd.read_html(html_path)
      df.append(times)
      df=pd.concat(df)
      df.to_html(html_path,index=False)
    logger.debug("saving dataframe to excel")
    excel_path=getfilepath("times.xlsx")
    if not os.path.exists(excel_path):
      times.to_excel(excel_path,index=False)
    else:
      df=pd.read_excel(excel_path)
      df=pd.concat([df,times])
      df.to_excel(excel_path,index=False)
  except Exception as e:
    logger.error("Error accurred while exporting dataframe: {}".format(e))
    logger.error(e)
  logger.info("times succesfully exported!")
logger.info("Finished.")
