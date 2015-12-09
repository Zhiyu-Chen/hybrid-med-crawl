from bs4 import BeautifulSoup
import urllib2
import re
import time
import sys
import scrapy
from scrapy.selector import Selector
from scrapy.linkextractors import LinkExtractor
from scrapy.http import HtmlResponse
import json

#http://www.utf8-chartable.de/unicode-utf8-table.pl?start=8192&number=128&utf8=string-literal



extractor = {
    'next_page': LinkExtractor(allow=r'http://www.medhelp.org/forums/Diabetes---Type-2/show/46(.*)'),
    'post_page': LinkExtractor(allow=r'http://www.medhelp.org/posts/Diabetes---Type-2/.*/show/(\d+)$'),
    'poster_page': LinkExtractor(allow=r'http://www.medhelp.org/personal_pages/user/\d+'),
}

old_path = {
    'title': '/html/body/div[4]/div[1]/div/div[1]/div[1]/div[1]/div[2]/text()',
    #'/html/head/title/text()',
    'reply_num': '//*[@id="comments_header"]/span/text()',
    'qa': '//div[@class="KonaBody"]',
    # 'qa' : '//div[@class="KonaBody"]/text()[preceding-sibling::br]',
}

new_path = {
    'title': '//*[@id="post_question_header"]/div[2]/div[1]/text()',
    # title = response.xpath('//*[@id="post_question_header"]/div[2]/div[1]/text()').extract()[0].strip()
    'reply_num': '//*[@id="post_answer_header"]/div[1]/text()',
    # reply_num = int(response.xpath('//*[@id="post_answer_header"]/div[1]/text()').extract()[0].strip().split(' ')[0])
    'qa': '//div[@class="post_message_container"]/div[@class="post_message fonts_resizable"]',
    # re.sub(r'<div(.*)none">|<div class(.*)</div>|\xa0|</div>|<br>|\t|\n|\r','',qa[0].extract()).strip()
}


def get_userinfo(user_page):
    demo = []
    interest = []
    user_req = urllib2.Request(user_page, headers={'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"})
    try:
        user_html = urllib2.urlopen(user_req)
    except urllib2.HTTPError, e:
        print e.code
        print e.read()
        return demo,interest
    except urllib2.URLError, e:
        print e.code
        return demo,interest
    except httplib.HTTPException, e:
        print e.code
        return demo,interest

    user_soup = BeautifulSoup(user_html, "lxml")  # soup for user homepage

    # find the user's interests
    for interest_sec in user_soup.find_all('span', {'class': 'interests_show'}):
        for interest_info in interest_sec.find_all('a'):
            interest.append(interest_info.get_text().strip())

    # find the user's demo_info
    for demo_sec in user_soup.find_all('div', {'class': 'bottom float_fix'}):
        demo_sec2 = demo_sec.find_all('div', {'class': 'section'})[0]
        num = 0
        for demo_info in demo_sec2.find_all('span'):
            if (num > 0 and num < 4):
                if '' != demo_info.get_text().strip():
                    demo.append(demo_info.get_text().strip())
            num = num + 1

    return demo, interest




def getQA(qa):
    str = re.sub(r'\n|\t|<div class="KonaBody">|</div>|<br>|\r|\xa0|\xe2\x80\x94|\xe2\x80\x99|\xe2\x80\xa6|\xe2\x80\x9c|\xe2\x80\x9d|\xe2\x80\xa2|&gt;|&lt;',' ',qa)
    str = re.sub(r'\xe2\x80\x99',r"'",str)
    return str.strip()

'''
crawling the following items from the medhelo.org:
1.title of post that satisfies specific conditions;
2.user information:
  2.1 demo info
  2.2 interests of diseases
3.questions
4.replies
'''
# ----------------------------------------------main---------------------------------------------------------------
reload(sys)
sys.setdefaultencoding('utf8')
#sys.setdefaultencoding('iso8859-1')

file = open('data.json', 'wb')
for page_Number in range(0, 232):
    link = "http://www.medhelp.org/forums/Diabetes---Type-2/show/46?page=" + str(page_Number + 1)
    req = urllib2.Request(link, headers={
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"})

    try:
        community_page = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        print e.code
        print e.read()
        continue
    except urllib2.URLError,e:
        print e.code
        print e.read()
        continue
    except httplib.HTTPException,e:
        print e.code()
        print e.read()
        continue

    soup = BeautifulSoup(community_page, "lxml")

    #for all the post urls in this page
    response = HtmlResponse(url=link, body=str(soup))
    for page_url in extractor['post_page'].extract_links(response):
        req = urllib2.Request(page_url.url, headers={
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36"})
        try:
            post_page = urllib2.urlopen(req)
        except urllib2.HTTPError,e:
                print e.code
                print e.read()
                continue
        except urllib2.URLError,e:
                print e.code
                print e.read()
                continue
        except httplib.HTTPException,e:
                print e.code()
                print e.read()
                continue
        post_soup = BeautifulSoup(post_page, "lxml")
        post_response = HtmlResponse(url=page_url.url, body=str(post_soup))
        path = old_path
        version = 0 # 0: old 1:new
        reply_num = post_response.xpath(path['reply_num']).extract()
        if reply_num == []:
            version = 1
            #print "new verion!"
            path = new_path
            reply_num = post_response.xpath(path['reply_num']).extract()
            if reply_num == []:
                reply_num = 0
            else:
                reply_num = int(reply_num[0].strip().split(' ')[0])
        else:
            reply_num = int(reply_num[0].strip().split(' ')[0])
            #print "old version"

        if reply_num == 0:
            continue

        #fill post info
        url = page_url.url
        post_id = url.split('/')[-1]
        title = str(post_response.xpath(path['title']).extract()[0]).strip()

        #fill question and replies
        allQA = post_response.xpath(path['qa']).extract()
        question = []
        answer = []
        if version == 0:
            question = getQA(allQA[0])
            for i in range(1,len(allQA)):
                answer.append(getQA(allQA[i]))
        else:
            question= re.sub(r'<div(.*)none">|<div class(.*)</div>|\xa0|\xe2\x80\x99|&gt;|&lt;|\xe2\x80\x94|\xe2\x80\xa6|\xe2\x80\x9c|\xe2\x80\x9d|\xe2\x80\xa2|</div>|<br>|\t|\n|\r',' ',allQA[0].strip())
            question = re.sub(r'\xe2\x80\x99',r"'",question).strip()
            for i in range(1,len(allQA)):
                astring = re.sub(r'<div(.*)none">|<div class(.*)</div>|\xa0|\xe2\x80\x99|&gt;|&lt;|\xe2\x80\x94|\xe2\x80\xa6|\xe2\x80\x9c|\xe2\x80\x9d|\xe2\x80\xa2|</div>|<br>|\t|\n|\r',' ',allQA[i].strip())
                answer.append(re.sub(r'\xe2\x80\x99',r"'",astring).strip())
        #fill poster info
        poster_url = extractor['poster_page'].extract_links(post_response)[0].url
        poster_id = poster_url.split('/')[-1]
        [demo,interest] = get_userinfo(poster_url)

        print "title %s " %title

        item = {'title':title,
                'reply_num': reply_num,
                'post_id':post_id,
                'url':url,
                'poster_id':poster_id,
                'poster_demo':demo,
                'poster_interests':interest,
                'question':question,
                'replies':answer}
        print answer
        string = json.dumps(item)
        file.write(string)
        file.write('\n')
file.close()





