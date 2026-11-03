"""Real shared control store/socket -> original DIO send interposition."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest

from public_paths import NATIVE, ROOT
VDATA = ROOT / "modules/carplay/source/vehicle-data"
DIO_TAP = NATIVE / "mibr_gps_dio_tap_experimental.c"

def nmea(body):
    crc = 0
    for b in body.encode(): crc ^= b
    return "$%s*%02X\\r\\n" % (body, crc)

@unittest.skipUnless(DIO_TAP.is_file(), "Research-only experimental DIO sender tap is omitted from the public source tree")
class SharedOwnerRuntime(unittest.TestCase):
    def test_manual_choice_live_original_sender_and_reconnect(self):
        cc = shutil.which(os.environ.get("CC", "cc"))
        self.assertIsNotNone(cc)
        with tempfile.TemporaryDirectory(prefix="gps-manual-") as tmp:
            out = Path(tmp)
            mode, control = out / "choice", out / "owner.sock"
            vendor, caller = out / "vendor.c", out / "caller.c"
            vendor.write_text(r'''
#include <stdio.h>
static int h;
int *iap2_connect(char *path,int flags){(void)path;return flags==91?&h:0;}
int iap2_disconnect(int *p){return p==&h?37:-1;}
int iap2_gps_data_send(void *p,const char *m){if(p!=&h)return -1;printf("VENDOR:%s\n",m);return 23;}
''')
            stock = nmea("GPRMC,120000.00,A,5111.0000,N,01122.0000,E,5.5,123.4,261026,,,A")
            caller.write_text(r'''
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
int *iap2_connect(char *,int);int iap2_disconnect(int *);int iap2_gps_data_send(void *,const char *);
int main(void){char line[128],reply[128];int *h=0,rc=0;
 int (*control)(void*,const char*,const char*,const char*,char*,size_t)=dlsym(RTLD_DEFAULT,"mibr_gps_demo_ipc");
 setvbuf(stdout,0,_IOLBF,0);
 while(fgets(line,sizeof(line),stdin)){
  if(!strncmp(line,"CONNECT",7)){h=iap2_connect("/dev/fixture",91);rc=h?0:-1;}
  else if(!strncmp(line,"DISCONNECT",10)){rc=iap2_disconnect(h);h=0;}
  else if(!strncmp(line,"SELECT ",7)){line[strcspn(line,"\n")]=0;rc=control(0,"SET",line+7,"987",reply,sizeof(reply));printf("REPLY:%s\n",reply);}
  else if(!strncmp(line,"GET",3)){rc=control(0,"GET",0,0,reply,sizeof(reply));printf("REPLY:%s\n",reply);}
  else if(!strncmp(line,"BAD",3))rc=iap2_gps_data_send(h,"$GPGLL,bad*00");
  else rc=iap2_gps_data_send(h,"''' + stock + r'''");
  printf("DONE:%d\n",rc);
 }
 return 0;
}
''')
            def build(args):
                r = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            build([cc,"-std=gnu99","-Wall","-Wextra","-Werror","-fPIC","-shared",str(vendor),"-o",str(out/"libvendor.so")])
            library = out / "libowner.so"
            units = ["mibr_gps_dio_runtime.c",
                     "mibr_gps_demo.c","mibr_gps_demo_owner.c","mibr_gps_demo_mode.c","mibr_gps_demo_ipc.c"]
            build([cc,"-std=gnu99","-Wall","-Wextra","-Werror","-fPIC","-shared","-DMIBR_GPS_HOST_INTERPOSITION_TEST",
                   '-DMIBR_GPS_DEMO_MODE_FILE="%s"'%mode, '-DMIBR_GPS_DEMO_SOCKET="%s"'%control,
                   "-I",str(NATIVE),"-I",str(VDATA)] + [str(NATIVE/x) for x in units] +
                  [str(VDATA/x) for x in ("mvs_core.c","mibr_vdata.c","mibr_vstatus.c","mibr_vdata_hook.c")] +
                  ["-o",str(library),"-ldl","-pthread"])
            executable = out / "caller"
            build([cc,"-std=gnu99","-Wall","-Wextra","-Werror",str(caller),"-L",str(out),"-lvendor","-Wl,-rpath,"+str(out),"-ldl","-o",str(executable)])
            process = subprocess.Popen([str(executable)],env=dict(os.environ,LD_PRELOAD=str(library)),
                                       stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            def command(text):
                process.stdin.write(text+"\n");process.stdin.flush();lines=[]
                while True:
                    raw=process.stdout.readline()
                    self.assertTrue(raw,"caller terminated")
                    line=raw.strip()
                    if line.startswith("DONE:"): return int(line[5:]),lines
                    if line: lines.append(line)
            def request(text):
                with socket.socket(socket.AF_UNIX) as s:
                    s.settimeout(2);s.connect(str(control));s.sendall((text+"\n").encode());return s.recv(256).decode()
            try:
                self.assertEqual(command("GET"),(0,["REPLY:OK OFF 0 0 0"]))
                self.assertEqual(command("SELECT BERLIN_DEMO"),(0,["REPLY:OK BERLIN_DEMO 0 0 0"]))
                self.assertEqual(mode.stat().st_mode & 0o777,0o600)
                self.assertEqual(command("CONNECT")[0],0)
                self.assertIn("5231.3235,N,01324.9731,E"," ".join(command("SEND")[1]))
                self.assertEqual(command("SELECT HAMBURG_DEMO")[0],0)
                rc,frames=command("SEND");self.assertEqual(rc,23)
                self.assertIn("5333.1453,N,00959.7258,E"," ".join(frames))
                self.assertEqual(command("BAD"),(0,[]))
                self.assertEqual(command("DISCONNECT")[0],37)
                self.assertIn("HAMBURG_DEMO"," ".join(command("GET")[1]))
                self.assertEqual(command("CONNECT")[0],0)
                self.assertIn("5333.1453,N,00959.7258,E"," ".join(command("SEND")[1]))
                self.assertEqual(command("SELECT OFF")[0],0)
                self.assertIn("5111.0000,N,01122.0000,E,5.5,123.4"," ".join(command("SEND")[1]))
                errors=[]
                def controls():
                    try:
                        for i in range(15):
                            self.assertTrue(request("GET").startswith("OK OFF"))
                    except BaseException as e: errors.append(e)
                t=threading.Thread(target=controls);t.start()
                for i in range(15): self.assertEqual(command("SEND")[0],23)
                t.join(3);self.assertFalse(t.is_alive());self.assertFalse(errors,errors)
                self.assertEqual(command("DISCONNECT")[0],37)
            finally:
                process.stdin.close();process.wait(timeout=5)
                self.assertEqual(process.returncode,0,process.stderr.read())
                process.stdout.close();process.stderr.close()
            self.assertFalse(control.exists())
            self.assertTrue(mode.exists()) # choice lasts until OFF/Unit reboot, not session reset

if __name__=="__main__": unittest.main()
