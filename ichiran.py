#!/usr/bin/python
import subprocess
import json


class ichiran:

    def __init__(self, msg):
        """ Init ichiran message """
        self.msg = msg

    def info(self):
        """ Get basic info for the message """
        cmd = "ichiran.exe -i " + self.msg
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        (output, err) = proc.communicate()
        status = proc.wait()
        parsed = ""
        if (status == 0):
            parsed = output.decode('utf-8')
        return parsed

    def full(self):
        """ Get full info for the message """
        cmd = "ichiran.exe -f " + self.msg
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        (output, err) = proc.communicate()
        status = proc.wait()
        parsed = []
        if (status == 0):
            json_output = json.loads(output)
            parsed = json_output[0][0][0]
        return parsed


#print(ichiran("一覧は最高だぞ").info())
#print(ichiran("一覧は最高だぞ").full())
