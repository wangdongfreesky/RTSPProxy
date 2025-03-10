import re
import time
import datetime
import requests
import gzip
#$$$必改项！！！鉴权验证，频道地址，频道logo，节目单的服务器地址，需要抓包改成你自己的
IPTVServer = 'http://192.168.37.11:33200'
#给内网提供直播服务的主机IP，也就是软路由的地址，udpx本程序不提供
#用于直播的代理端口号
LivePort = '4022'
#用于回看的代理端口号
ReplayPort = '554'
#提供logo文件的服务器端口号
WebPort= '2000'
#内网代理服务器IP地址
LanServer = '192.168.50.3'
#外网访问的域名
NetServer = 'wangdongqq.tpddns.cn'
######节目单和播放地址列表文件名称可以改成你自己的，路径别动
web_path = r'/app/output/lighttps/root/'
playlist = 'PL.xml'
playlistgz = 'PL.xml.gz'
#用于生成不同类型的播放列表的文件路径
LanReplay_name = 'LanReplay.m3u'  # 输出M3U文件路径
LanLive_name = 'LanLive.m3u' 
NetLive_name = 'NetLive.m3u'
NetReplay_name = 'NetReplay.m3u'
###以上是一些参数设定，可根据需要修改,此外鉴权的部分，也要根据自己抓包修改
###################################################################
# 鉴权验证
def getValidAuthenticationHWCTC():
    session = requests.Session()
    #$$$鉴权验证，提交的数据抓包获得，需要改成你自己的
    form_data = {"UserID":"ip15519994075@itv", "Lang":"1", "SupportHD":"1", "NetUserID":"", "Authenticator":"3E3071B2728A64B809A36EBA5BA8DAD92CF454189488B73C1A98D6CCADD265D1865BD2BB1CA9F78AFF3CEF8EC64557DAF6B88C2E88E8BDDB9ED4975C881BFAC36A14C6520D837B8982BFD5EED154F3AB2469FEB770881870EA860F83E183EDDE4EDC27171FE0AE43B8290EA134C53A3B48C864576901F15AAA78CEFB5538A08F", "STBType":"EC6108V9U_pub_hbjdx", "STBVersion":"V100R003C82LHED01B015", "conntype":"4", "STBID":"00100399006068901604002126191A8F", "templateName":"hbdxggpt", "areaId":"8130335", "userToken":"573917B51460505F7646F26B209DA124", "userGroupId":"1", "productPackageId":"-1", "mac":"00:21:26:19:1A:8F", "UserField":"2","SoftwareVersion":"V100R003C82LHED01B015", "IsSmartStb":"0", "desktopId":"","stbmaker":"", "XMPPCapability":"1", "ChipID":"","VIP":""}
    response = session.post(IPTVServer+'/EPG/jsp/ValidAuthenticationHWCTC.jsp',data=form_data)
    #返回经过验证的会话
    return session
#根据序号确定是否重新验证，如需修改间隔，则修改Frequency参数，例如每100次重新鉴权
def ReValidAuthentication(index):
    Frequency = 60
    return (index - 1) % Frequency == 0
#根据台号进行分组，返回分组名称
def getgrouptitle(NOs):
    if int(NOs, base=10) < 20:
        group_title = '央视台'
    elif int(NOs, base=10) < 130:
        group_title = '河北省台'
    elif int(NOs, base=10) < 200:
        group_title = '河北市级台'
    elif int(NOs, base=10) < 400:
        group_title = '全国卫视'
    elif int(NOs, base=10) < 500:
        group_title = '数字标清'
    elif int(NOs, base=10) < 600:
        group_title = '数字高清'
    elif int(NOs, base=10) < 700:
        group_title = '数字直播'
    elif int(NOs, base=10) < 900:
        group_title = '县级台'
    else:
        group_title = '其他'
    return group_title
#获取频道列表和播放地址
def getchannellist():
    channeldata = [] #构造用于返回的频道数据
    #获取频道列表的post表单提交用于得到含有播放地址的数据
    session = getValidAuthenticationHWCTC()
    response = session.post(IPTVServer+'/EPG/jsp/getchannellistHWCTC.jsp')
    #返回的结果字符串
    channel_text = response.text
    # 提取频道名称和链接
    channel_ID = re.findall(r'\bChannelID="(.*?)"', channel_text)
    channel_names = re.findall(r'ChannelName="(.*?)"', channel_text)
    userchannel_ID = re.findall(r'UserChannelID="(.*?)"', channel_text)
    channel_urls = re.findall(r'ChannelURL="(.*?)"', channel_text)
    #对播放地址再次匹配，提取有用数据，并对频道进行分组 
    index = 1
    for channelID, channelname, userchannelID, url in zip(channel_ID, channel_names, userchannel_ID, channel_urls):
        # 分别保留rtsp和igmp链接，并过滤掉无用的部分
        # 只保留rtsp部分，去掉igmp部分
        igmp_link = re.search(r'igmp://([^\s|]+)', url)  # 匹配igmp链接的ip地址部分
        rtsp_link = re.search(r'(rtsp://[^\s|]+smil)', url)  # 匹配rtsp链接
        group_title = getgrouptitle(userchannelID)
        if rtsp_link:
            #将相关数据整合，序号，频道id，频道名称，频道号，分组标题，rtsp地址，igmp地址
            channeldata.append((index, channelID, channelname, userchannelID, group_title, rtsp_link.group(1), igmp_link.group(1)))
            index += 1
    return channeldata
#获取节目单数据
def getplaylist(channeldata):
    #用于返回的数据
    playlistdata = []
    #六天之前的凌晨，一天时间为86400000，六天为518400000
    limittime = int(round(time.mktime(datetime.date.today().timetuple()) * 1000)) - 518400000 #支持的最早时间六天前0点
    headers= {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With":"XMLHttpRequest",}
    for index, channelID, channelname, userchannelID, group_title, rtspurl, igmpurl in channeldata:
        #一次鉴权后查询的数据有限最多大概到四百个频道左右，未避免遗漏，每100个频道重新鉴权验证
        if ReValidAuthentication(index):
            session = getValidAuthenticationHWCTC()
        Tendaysdata = []
        starttime = limittime
        #能查出10天的节目单，但是APTV不支持，只支持7天回看（含当天）一天预告，央视台可支持3天预告，如有需要
        #将字符串改为"0123456789"
        for once in '12345678':
            data = {
                "queryChannel":{
                    "channelIDs":[channelID]},
                "queryPlaybill":{
                    "type":"0",
                    "startTime":starttime,
                    "endTime":starttime + 86400000,
                    "count":"100",
                    "offset":"0",
                    "isFillProgram":"0",
                    "mustIncluded":"0"},
                "needChannel":"0"}
            response = session.post(IPTVServer+'/VSP/V3/QueryPlaybillList', headers=headers, json=data)
            starttime += 86400000
            dayplaydata = formatdayplaydata(response.text)
            Tendaysdata.append((dayplaydata))  
        #频道id，频道号，频道名称，该频道十天节目单
        playlistdata.append((channelID,userchannelID,channelname,Tendaysdata))
    return playlistdata
#从返回的节目单字符串中提取相关数据
def formatdayplaydata(playlisttext):
    #用于返回的数据
    dayplaydata = []
    ##匹配出一天的节目单
    clean_text = re.findall(r'(startTime":".*?endTime":".*?)"', playlisttext)  
    #将节目单中的<>符号替换为《》，以免被错误解读，这是替换表
    trantab = str.maketrans({'<': '《', '>': '》'})
    for playlist_text in clean_text:
        channelID = re.search(r'channelID":"(.*?)"', playlist_text)  # 匹配频道ID
        starttime_str = re.search(r'startTime":"(.*?)"', playlist_text)  # 匹配开始时间
        name_str = re.search(r'name":"(.*?)"', playlist_text)  # 匹配节目名       
        endtime_str = re.search(r'endTime":"(.*)', playlist_text)  # 匹配结束时间
        #对节目名称进行符号替换
        if name_str:
            playname = name_str.group(1).translate(trantab)
        #将开始时间和结束时间转换为时移代码 
        if starttime_str:
            startTime = time.strftime("%Y%m%d%H%M%S", time.localtime(int(starttime_str.group(1))/1000)) + " +0800"
        if endtime_str:
            endTime = time.strftime("%Y%m%d%H%M%S", time.localtime(int(endtime_str.group(1))/1000)) + " +0800"
        dayplaydata.append((channelID.group(1),startTime,playname,endTime))
    return dayplaydata 
# 生成带有内网组播转单播服务器地址的M3U文件仅可用于直播，不可回看
def generate_LanLivem3u(channeldata):
    LanLive_path = web_path + LanLive_name #路径及文件名
    epg_url = 'http://' + LanServer + ':' + WebPort + '/' + playlistgz
    with open(LanLive_path, 'w', encoding='utf-8') as httpfile:
        httpfile.write(f'#EXTM3U name="河北电信IPTV" x-tvg-url="{epg_url}"\n')  # M3U文件头
        # 写入已排序的频道信息
        for index, channelID, channelname, userchannelID, group_title, rtspurl, igmpurl in channeldata:
            # 写入频道信息和RTSP链接，按照指定格式
            lanliveurl = "http://" + LanServer + ":" + LivePort + "/udp/" + igmpurl
            channellogo = "http://" + LanServer + ":" + WebPort + "/logo/" + userchannelID + ".png"
            httpfile.write(f'#EXTINF:-1 tvg-id="{userchannelID}" tvg-name="{channelname}" tvg-logo="{channellogo}" group-title="{group_title}", {channelname}\n')
            httpfile.write(f'{lanliveurl}\n')  # 空白行分隔
    print(f'M3U文件已生成：{LanLive_path}')
# 生成带有rtsp地址可回看的M3U文件
def generate_LanReplaym3u(channeldata):
    LanReplay_path = web_path + LanReplay_name   #输出M3U文件路径及文件名
    epg_url = 'http://' + LanServer + ':' + WebPort + '/' + playlistgz
    with open(LanReplay_path, 'w', encoding='utf-8') as rtspfile:
        rtspfile.write(f'#EXTM3U name="河北电信IPTV" x-tvg-url="{epg_url}" catchup="append" catchup-source="?playseek=${{(b)yyyyMMddHHmmss}}-${{(e)yyyyMMddHHmmss}}"\n')  # M3U文件头
        # 写入已排序的频道信息
        for index, channelID, channelname, userchannelID, group_title, rtspurl, igmpurl in channeldata:
            channellogo = "http://" + LanServer + ":" + WebPort + "/logo/" + userchannelID + ".png"
            # 写入频道信息和RTSP链接，按照指定格式
            rtspfile.write(f'#EXTINF:-1 tvg-id="{userchannelID}" tvg-name="{channelname}" tvg-logo="{channellogo}" group-title="{group_title}", {channelname}\n')
            rtspfile.write(f'{rtspurl}\n')  # 空白行分隔  
    print(f'M3U文件已生成：{LanReplay_path}')
# 生成带有域名地址的M3U文件，可用于外网访问直播，主路由需要开启相关端口映射，内网使用也可但不推荐，不可回看
def generate_NetLivem3u(channeldata):
    NetLive_path = web_path + NetLive_name #路径及文件名
    epg_url = 'http://' + NetServer + ':' + WebPort + '/' + playlistgz
    with open(NetLive_path, 'w', encoding='utf-8') as ddnsfile:
        ddnsfile.write(f'#EXTM3U name="河北电信IPTV" x-tvg-url="{epg_url}"\n')  # M3U文件头
        # 写入频道信息
        for index, channelID, channelname, userchannelID, group_title, rtspurl, igmpurl in channeldata:
            netliveurl = "http://" + NetServer + ":" + LivePort + "/udp/" + igmpurl
            channellogo = "http://" + NetServer + ":" + WebPort + "/logo/" + userchannelID + ".png"
            # 写入频道信息和http链接，按照指定格式
            ddnsfile.write(f'#EXTINF:-1 tvg-id="{userchannelID}" tvg-name="{channelname}" tvg-logo="{channellogo}" group-title="{group_title}", {channelname}\n')
            ddnsfile.write(f'{netliveurl}\n')  # 空白行分隔
    print(f'M3U文件已生成：{NetLive_path}')
def generate_NetReplaym3u(channeldata):
    NetReplay_path = web_path + NetReplay_name
    epg_url = 'http://' + NetServer + ':' + WebPort + '/' + playlistgz
    with open(NetReplay_path, 'w', encoding='utf-8') as ddnsfile:
        ddnsfile.write(f'#EXTM3U name="河北电信IPTV" x-tvg-url="{epg_url}" catchup="append" catchup-source="?playseek=${{(b)yyyyMMddHHmmss}}-${{(e)yyyyMMddHHmmss}}"\n')  # M3U文件头
        # 写入频道信息
        for index, channelID, channelname, userchannelID, group_title, rtspurl, igmpurl in channeldata:
            suffix_link = re.search(r'(/PLTV/[^\s|]+smil)', rtspurl)  # 去掉rtsp及ip地址部分
            netreplayurl = "rtsp://" + NetServer + ":" + ReplayPort + suffix_link.group(1)
            channellogo = "http://" + NetServer + ":" + WebPort + "/logo/" + userchannelID + ".png"
            # 写入频道信息和RTSP链接，按照指定格式
            ddnsfile.write(f'#EXTINF:-1 tvg-id="{userchannelID}" tvg-name="{channelname}" tvg-logo="{channellogo}" group-title="{group_title}", {channelname}\n')
            ddnsfile.write(f'{netreplayurl}\n')  # 空白行分隔
    print(f'M3U文件已生成：{NetReplay_path}')
# 生成epg电子节目单文件，节目单文件可以配合rtsp地址进行回看，直播也可看到节目预告
def generate_playlist(playlistdata):
    playlist_path = web_path + playlist  # 输出节目单路径
    with open(playlist_path, 'w', encoding='utf-8') as playlistfile:
        playlistfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')  # M3U文件头
        playlistfile.write('<tv info-name="河北电信EPG" info-url="">\n')  # M3U文件头
        for channelID, userchannelID, channelname, Tendaysdata in playlistdata:
            playlistfile.write(f'<channel id="{userchannelID}">\n<display-name lang="zh">{channelname}</display-name>\n</channel>\n')
            for dayplaydata in Tendaysdata:
                for channelID,startTime,playname,endTime in dayplaydata:
                    playlistfile.write(f'<programme channel="{userchannelID}" start="{startTime}" stop="{endTime}">\n<title lang="zh">{playname}</title>\n</programme>\n')
        playlistfile.write('</tv>')
    print(f'xml文件已生成：{playlist_path}')
def generate_playlistgz():
    playlist_path = web_path + playlist  # 输出节目单路径
    playlistgz_path = web_path + playlistgz  # 输出节目单路径
    with open(playlist_path, 'r', encoding='utf-8') as playlistfile:
        playlistdata = playlistfile.read()
    with gzip.open(playlistgz_path,"wb") as playlistgzfile:
        playlistgzfile.write(playlistdata.encode('utf-8'))
    print(f'gz文件已生成：{playlistgz_path}')
#程序入口
if __name__ == '__main__':
    #提取频道数据及地址
    channeldata = getchannellist()
    # 根据频道数据并生成M3U文件
    generate_LanReplaym3u(channeldata)
    generate_LanLivem3u(channeldata)
    generate_NetLivem3u(channeldata)
    generate_NetReplaym3u(channeldata)
    #提取节目单数据
    playlistdata = getplaylist(channeldata)
    # 根据频道数据并生成xml文件，有先后顺序，必须先生成xml然后压缩
    generate_playlist(playlistdata)
    generate_playlistgz()
