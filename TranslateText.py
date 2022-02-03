#!/usr/bin/python3
import random
import requests
import configparser
from os import path
from hashlib import md5

# Generate salt and sign


def make_md5(s, encoding='utf-8'):
    return md5(s.encode(encoding)).hexdigest()


class TranslateText(object):

    def __init__(self, cfgfile="config.ini"):
        # See https://docs.python.org/3/library/configparser.html
        config = configparser.ConfigParser()
        config.read(cfgfile)
        # Set your own appid/apikey in config.ini
        self.appid = config['api.fanyi.baidu.com']['appid']
        self.apikey = config['api.fanyi.baidu.com']['apikey']
        print("appid=" + self.appid)
        print("apikey=" + self.apikey)

    def translate(self, text, from_lang='jp', to_lang='zh'):
        # For list of language codes, please refer to `https://api.fanyi.baidu.com/doc/21`
        endpoint = 'http://api.fanyi.baidu.com'
        path = '/api/trans/vip/translate'
        url = endpoint + path

        salt = random.randint(32768, 65536)
        sign = make_md5(self.appid + text + str(salt) + self.apikey)

        # Build request
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {'appid': self.appid, 'q': text, 'from': from_lang,
                   'to': to_lang, 'salt': salt, 'sign': sign}

        # Send request
        r = requests.post(url, params=payload, headers=headers)
        result = r.json()

        # Show response
        trans_result = result["trans_result"]
        result_text = ""
        for i in range(len(trans_result)):
            dst = trans_result[i]["dst"].strip()
            if (len(dst) > 0):
                result_text += dst + "\n"
        return result_text

#print(TranslateText().translate("日本語の勉強を楽しんでいますか？"))
