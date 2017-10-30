import requests
from urllib.parse import urlencode
from requests.exceptions import ConnectionError
from pyquery import PyQuery as pq
import pymongo
from config import *

client = pymongo.MongoClient(MONG_URL)
db = client[MONG_DB]

base_url = 'http://weixin.sogou.com/weixin?'

headers = {  #从网页源码获取cookie等信息构造headers
	'Cookie':'IPLOC=CN4501; SUID=08D658B62513910A0000000059E85DBB; SUV=1508400577388643; ABTEST=7|1508400594|v1; SNUID=C8169809BFC5E4212123ED14C0BFE527; weixinIndexVisited=1; sct=2; JSESSIONID=aaasvxeJwKkfH_XPukv8v',
	'Host':'weixin.sogou.com',
	'Referer':'http://weixin.sogou.com/weixin?type=2&query=%E9%A3%8E%E6%99%AF&ie=utf8&s_from=input&_sug_=y&_sug_type_=&w=01019900&sut=2562&sst0=1508400608056&lkt=1%2C1508400607949%2C1508400607949',
	'Upgrade-Insecure-Requests':'1',
	'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
}



proxy = None  #全局变量（开始不设置代理）
max_count = 5 #请求次数

def get_proxy():
	try:
		response = requests.get(PROXY_POOL_URL)
		if response.status_code == 200:
			return response.text
		return None

	except ConnectionError:
		return None



def get_html(url,count=1):
	print('Crawling',url)
	print('Trying Count',count)  
	global proxy
	if count >=max_count:
		print('Tried Too Many Counts')
		return None
	try:
		if proxy:
			proxies={
				'http':'http//'+proxy
			}
			response = requests.get(url,allow_redirects=False,headers=headers)  #参数redirect设为false防止自动跳转302页面
		else:
			response = requests.get(url,allow_redirects=False,headers=headers)  #参数redirect设为false防止自动跳转302页面
		if response.status_code == 200:
 			return response.text    #请求成功返回网页源代码
		if response.status_code == 302:
 			# need proxy  代理被封，需要设置代理
 			print('302')
 			proxy = get_proxy()
 			if proxy:
 				print('Using proxy',proxy)
 				count +=1
 				return get_html(url)
 			else:
 				print('Get Proxy Failed')
 				return None

	except ConnectionError as e:
		print('Error Occurred',e.args)
		proxy = get_proxy()
		count += 1

		return get_html(url,count)   #请求失败则继续请求






def get_index(keyword,page):
	data = {
		'query':keyword,
		'type':2,
		'page':page

	}

	quesies = urlencode(data)   #编码，变成get请求参数
	url = base_url + quesies    #完整的url
	html = get_html(url)
	return html


def parse_index(html):
	doc = pq(html)
	items = doc('.new-box .new-list li .text-box h3 a ').items()
	for i in items:
		yield item.attr('href')

def get_detail(url):
	try:
		response = requests.get(url)
		if response.status_code == 200:
			return response.text
		return None
	except ConnectionError:
		return None

def parse_detail(html):
	doc = pq(html)
	title = doc('.rich_media_title').text()
	content = doc('.rich_media_content').text()
	date = doc('post-date').text()
	nickname = doc('#js_profile_qrcode > div > strong').text()
	wechat = doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()  #公众号账号
	return{
		'title':title,
		'content':content,
		'date':date,
		'nickname':nickname,
		'wechat':wechat
	}

def save_to_mongo(data):
	if db['artitles'].update({'title':data['title']},{'$set':data},True):
		print('Save to Mongo',data['title'])
	else: 
		print('Save to Mongo Failed ',data['title'])


def main():
	for page in range(1,101):
		html = get_index(KEYWORD,page)
		if html:
			article_urls=parse_index(html)
			for article_url in article_urls:
				article_html = get_detail(article_url)
				if article_html:
					article_data = parse_detail(article_urls)
					print(article_data)
					save_to_mongo(article_data)



if __name__ == '__main__':
	main()