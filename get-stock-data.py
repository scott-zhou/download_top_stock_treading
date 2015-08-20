#!/usr/bin/env python3

"""------------------Simple Use Guild----------------------------
"get-stock-data.py today" | "get-stock-data.py": will fetch data only for today. The parameter "today" can be ignor.
"get-stock-data.py all": wil fetch all datas. It will take very long time.
"get-stock-data.py SPECIAL_DATE": will fetch data only for the special date. The formate for date is yyyy-mm-dd, for example 2015-06-08
"get-stock-data.py START_DATE END_DATE": will fetch data from START_DATE to END_DATE. The formate for date is yyyy-mm-dd, for example 2015-06-08. START_DATE must be earlier than END_DATE
--------------------------------------------------------------
"""

__author__ = 'scott.cong.zhou@gmail.com (Scott Zhou)'

import sys
import time
import csv
import urllib.request
from html.parser import HTMLParser
from socket import timeout
import datetime

DOMAIN="http://data.eastmoney.com"
PAGES = 0
ONLY_TODAY = True
ALL_DATA = False
SPECIAL_DATE = []
EXITFLAG = False
LIST_FN = ''
DETAIL_FN = ''
CURRENT_PAGE_NUM = 1
SAVED = {}

def print_use_and_exit():
    print(__doc__)
    sys.exit(1)

def main(argv):
    print_use_and_exit()
    if len(argv)>3:
        print('Command error, please use this command like following:')
        print_use_and_exit()
    elif len(argv)<=1:
        ONLY_TODAY = True
        ALL_DATA = False
    elif len(argv)==2:
        if ('-' in argv[1]) and ('h' in argv[1]):
            print_use_and_exit()
        elif argv[1] == 'today':
            ONLY_TODAY = True
            ALL_DATA = False
        elif argv[1] == 'all':
            ONLY_TODAY = False
            ALL_DATA = True
        else:
            ONLY_TODAY = False
            ALL_DATA = False
            SPECIAL_DATE.append(argv[1])
    else: #len(argv)==3
        ONLY_TODAY = False
        ALL_DATA = False
        t = argv[1].split('-')
        startday = datetime.date(int(t[0]),int(t[1]),int(t[2]))
        t = argv[2].split('-')
        endday = datetime.date(int(t[0]),int(t[1]),int(t[2]))
        r = (endday-startday).days +1
        for i in range(r):
            d = startday+datetime.timedelta(i)
            SPECIAL_DATE.append(d.isoformat())

if __name__ == '__main__':
    main(sys.argv)



today = datetime.date.today().isoformat()

if ONLY_TODAY :
    SPECIAL_DATE.append(today)


if ALL_DATA:
    LIST_FN = 'all-list-{0}.csv'.format(today)
    DETAIL_FN = 'all-detail-{0}.csv'.format(today)
elif len(SPECIAL_DATE)==1:
    LIST_FN = '{0}-list.csv'.format(SPECIAL_DATE[0])
    DETAIL_FN = '{0}-detail.csv'.format(SPECIAL_DATE[0])
else:
    [x,*_,y] = SPECIAL_DATE
    LIST_FN = '{0}--{1}-list.csv'.format(x,y)
    DETAIL_FN = '{0}--{1}-detail.csv'.format(x,y)

def convertFloat(i):
    try:
        return False,'%.2f' % float(i)
    except:
        return True,'0.00'

def convertPercent(i):
    try:
        return False,'%.2f' % float(i.replace('%',''))+'%'
    except:
        return True,'0.00%'

class MyHTMLParser(HTMLParser):
    title_line = False
    lnum = 0
    date = ''
    code = ''
    name = ''
    atype = ''

    check_date_type = False
    date_correct = False
    type_correct = False
    found_table = False
    tbody = False
    df = []
    line = []
    keydata = False
    isin = True
    ignorThisLine = False

    def set_my_date(self, date, code, name, atype, detailfile):
        self.date = date
        self.code = code
        self.name = name
        self.atype = atype
        self.df = detailfile


    def handle_starttag(self, tag, attrs):
        if tag == 'div' and attrs == [('class', 'divtips')]:
            self.check_date_type = True
            #print('start check date and type in handle_data')
        elif self.found_table and tag == 'tbody':
            self.tbody = True
            #print('start tbody')
        elif self.tbody and tag == 'tr': #start line
            self.line.clear()
            direc = '卖出金额最大的前5名'
            if self.isin:
                direc = '买入金额最大的前5名'
            self.line = [self.date, self.name, self.code, self.atype, direc]
            #print('place to start a line')
        elif self.tbody and tag == 'td': #start colom
            self.keydata = True
            #print('place to start a colom')

    def handle_endtag(self, tag):
        if self.check_date_type and tag == 'div':
            if self.date_correct and self.type_correct:
                self.found_table = True
                #print('foundl correct table')
            self.check_date_type = False
            self.date_correct = False
            self.type_correct = False
            #print('finish div area')
        elif self.tbody and tag == 'tbody':
            self.tbody = False
            if self.isin:
                self.isin = False
                #print('finish first tbody')
            else:
                self.found_table = False
                #print('stop handle any table data')
        elif self.tbody and tag == 'tr': #stop line
            if not self.ignorThisLine:
                #data at pos 7,8,9,10 are 买入金额(万)  占总成交比例    卖出金额(万)    占总成交比例
                #if any of the previous ones are changes, pos 11 (净额(万)) need canculate
                if len(self.line)==11:
                    # it will happen that the 交易营业部名称 is not existed.
                    # when it happen, we must insert a empty string to occpuied the list pos 6
                    self.line.insert(6, '')
                a,self.line[7] =convertFloat(self.line[7])
                b,self.line[8] =convertPercent(self.line[8])
                c,self.line[9] =convertFloat(self.line[9])
                d,self.line[10]=convertPercent(self.line[10])
                if a or b or c or d:
                    self.line[11]=str(float(self.line[7])-float(self.line[9]))
                self.df.append(self.line[:])
            #print('finish a line')
        elif self.keydata and tag == 'td': #stop colom
            self.keydata = False
            #print('finish a colom')

    def handle_data(self, data):
        if self.check_date_type:
            if self.date in data:
                self.date_correct = True
            elif self.atype in data:
                self.type_correct = True
        elif self.keydata:
            #print('this is a key data')
            if len(self.line)==5 and (not data.isnumeric()):
                #Ignor the line if the first colum in the table is not a number
                self.ignorThisLine = True
            else:
                self.line.append(data)

def get_stock_detail(date,code,name,atype,detailfile):
    durl = DOMAIN + '/stock/lhb,' + date + ',' + code.split('.')[0] + '.html'
    content = ''
    success = False
    while not success:
        try:
            with urllib.request.urlopen(durl, timeout=10) as response:
                body = response.read()
                content = body.decode('gbk')
        except urllib.error.HTTPError:
            print('HTTP Error.')
            time.sleep(1)
        except urllib.error.URLError:
            print('URL Error.')
            time.sleep(1)
        except timeout:
            print('Timeout.')
            time.sleep(1)
        except:
            print('Other exception.')
            time.sleep(1)
        else:
            success = True

    parser = MyHTMLParser()
    parser.set_my_date(date, code, name, atype, detailfile)
    parser.feed(content)
    #print('FINISH ONE PAGE')



def proc_content(content):
    global PAGES,ONLY_TODAY,ALL_DATA,SPECIAL_DATE,LIST_FN,DETAIL_FN,EXITFLAG,CURRENT_PAGE_NUM,SAVED
    listfile = []
    detailfile = []
    clist = content.split(',,,')
    stocklist = clist[0].split('","')
    PAGES = int(clist[1].split(':')[1])

    for stock in stocklist:
        l = stock.replace('"', '')
        detail = l.split(',')
        atype = detail[0]
        detail[1] = str(float(int(float(detail[1])/100))/100)
        code = detail[2]
        detail[3] = str(float(int(float(detail[3])/100))/100)
        name = detail[4]
        date = detail[5]
        if len(SPECIAL_DATE)>0:
            #2015-05-08
            t = SPECIAL_DATE[0].split('-')
            rday = datetime.date(int(t[0]),int(t[1]),int(t[2]))
            t = date.split('-')
            lday = datetime.date(int(t[0]),int(t[1]),int(t[2]))
            if lday < rday:
                EXITFLAG = True
                break
        if (not ALL_DATA) and (date not in SPECIAL_DATE):
            continue
        if (date,name,atype) in SAVED:
            continue
        SAVED[(date,name,atype)] = True
        listfile.append(detail)
        print('Reading stock detail for {0} {1} {2}'.format(name, date, atype))
        get_stock_detail(date, code, name, atype, detailfile)
        if ALL_DATA: 
            print('Finish stock detail for {0}\t\t\t\t....{1}%'.format(name, int(float(CURRENT_PAGE_NUM)*100/float(PAGES))))
        else:
            print('Finish stock detail for {0}'.format(name))
    if len(listfile)>0:
        # open(LIST_FN, 'a', newline='', encoding='gbk') or open(LIST_FN, 'a', newline='')?
        # If you want the output can be readed on Windows OS (Chinese), encoding='gbk' is needed.
        # Otherwise, on my development env(Ubuntu, english language), encoding to gbk will not readable.
        # Same to all other csv R/W places(totallly 4 places in this script).
        with open(LIST_FN, 'a', newline='', encoding='gbk') as csvfile:
            w = csv.writer(csvfile)
            w.writerows(listfile)
    if len(detailfile)>0:
        with open(DETAIL_FN, 'a', newline='', encoding='gbk') as csvfile:
            w = csv.writer(csvfile)
            w.writerows(detailfile)


with open(LIST_FN, 'w', newline='', encoding='gbk') as csvfile:
    w = csv.writer(csvfile)
    w.writerow(['类型','机构席位卖出(万)','代码','机构席位买入(万)','股票名称','交易日期'])
with open(DETAIL_FN, 'w', newline='', encoding='gbk') as csvfile:
    w = csv.writer(csvfile)
    w.writerow(['交易日期','股票名称','代码','类型','买卖方向','序号','交易营业部名称','买入金额(万)','占总成交比例','卖出金额(万)','占总成交比例','净额(万)'])

while True:
    if EXITFLAG:
        exit()

    url = "http://datainterface.eastmoney.com/EM_DataCenter/JS.aspx?type=LHB&sty=JGXWMX&p={0}&ps=100&js=(x),,,pages:(pc),,,update:(ud)".format(CURRENT_PAGE_NUM)

    if PAGES > 0:
        print('Reading page {0}/{1}, 100 lines per page.'.format(CURRENT_PAGE_NUM,PAGES))
    else:
        print('Reading page {0}, 100 lines per page.'.format(CURRENT_PAGE_NUM))
    CURRENT_PAGE_NUM = CURRENT_PAGE_NUM + 1
    
    content = ''
    success = False
    while not success:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                body = response.read()
                content = body.decode('utf_8')
        except urllib.error.HTTPError:
            print('HTTP Error.')
            time.sleep(1)
        except urllib.error.URLError:
            print('URL Error.')
            time.sleep(1)
        except timeout:
            print('Timeout.')
            time.sleep(1)
        except:
            print('Other exception.')
            time.sleep(1)
        else:
            success = True

    proc_content(content)
    if CURRENT_PAGE_NUM>PAGES:
        break

