#importando moduli
import os
import sys

#definisco funzione per cancellare i file che hanno un nome che inizia per 'tempi'
def clear_tempi(path):
    for file in os.listdir(path):
        if file.startswith('tempi'):
            os.remove(os.path.join(path, file))
if __name__=='__main__':
    sys.stdout.write("---Cancello i file che iniziano per 'tempi'---\nPremi invio per continuare...")
    sys.stdin.readline()
    
    clear_tempi(os.getcwd())
    sys.stdout.write("---- Fine ----\nPremi invio per uscire...")
    sys.stdin.readline()
    sys.exit()