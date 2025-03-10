import re
import time
import datetime
import requests
#$$$必改项！！！鉴权验证，频道地址，频道logo，节目单的服务器地址，需要抓包改成你自己的
IPTVhost = 'http://192.168.37.11:33200'
######logo文件保存路径，路径别动
logo_path = r'/app/output/lighttps/root/logo/'  # 输出logo路径
# 鉴权验证
def getValidAuthenticationHWCTC():
    session = requests.Session()
    #$$$鉴权验证，提交的数据抓包获得，需要改成你自己的
    form_data = {"UserID":"ip15519994075@itv", "Lang":"1", "SupportHD":"1", "NetUserID":"", "Authenticator":"3E3071B2728A64B809A36EBA5BA8DAD92CF454189488B73C1A98D6CCADD265D1865BD2BB1CA9F78AFF3CEF8EC64557DAF6B88C2E88E8BDDB9ED4975C881BFAC36A14C6520D837B8982BFD5EED154F3AB2469FEB770881870EA860F83E183EDDE4EDC27171FE0AE43B8290EA134C53A3B48C864576901F15AAA78CEFB5538A08F", "STBType":"EC6108V9U_pub_hbjdx", "STBVersion":"V100R003C82LHED01B015", "conntype":"4", "STBID":"00100399006068901604002126191A8F", "templateName":"hbdxggpt", "areaId":"8130335", "userToken":"573917B51460505F7646F26B209DA124", "userGroupId":"1", "productPackageId":"-1", "mac":"00:21:26:19:1A:8F", "UserField":"2","SoftwareVersion":"V100R003C82LHED01B015", "IsSmartStb":"0", "desktopId":"","stbmaker":"", "XMPPCapability":"1", "ChipID":"","VIP":""}
    response = session.post(IPTVhost+'/EPG/jsp/ValidAuthenticationHWCTC.jsp',data=form_data)
    #返回经过验证的会话
    return session
#根据序号确定是否重新验证，如需修改间隔，则修改Frequency参数，例如每100次重新鉴权
def ReValidAuthentication(index):
    Frequency = 60
    return (index - 1) % Frequency == 0
#获取logo台标    
def getlogo():
    today_zero = int(round(time.mktime(datetime.date.today().timetuple()) * 1000)) #获取今日0点时间戳毫秒
    session = getValidAuthenticationHWCTC()
    response = session.post(IPTVhost+'/EPG/jsp/getchannellistHWCTC.jsp')
    # 提取频道号
    userchannel_ID = re.findall(r'UserChannelID="(.*?)"', response.text)
    #对播放地址再次匹配，提取有用数据，并对频道进行分组 
    index = 1
    for userchannelID in userchannel_ID:
        if ReValidAuthentication(index):
            session = getValidAuthenticationHWCTC()
        index += 1
        #构造用于查询频道logo的文件头
        headers= {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With":"XMLHttpRequest",}
        #构造提交的表单数据，抓包获得
        data = {
            "queryChannel":{
                "channelNOs":[userchannelID],
                "count":1},
            "queryPlaybillContext":{
                "date":today_zero,
                "type":1,
                "preNumber":1,
                "nextNumber":1}}
        response = session.post(IPTVhost+'/VSP/V3/QueryPlaybillContext', headers=headers, json=data)
        #通过正则表达式筛选出logo地址
        logo_str = re.search(r'(http://[^"^\s]*\.(png))', response.text)
        if logo_str:
            logo_url = logo_str.group(1)   
            print(f"获取到的图片链接：{logo_url}")
            logoresponse = requests.get(logo_url)
            # 检查请求是否成功
            if logoresponse.status_code == 200:
                # 将图片内容写入本地文件
                logoname = logo_path + userchannelID + ".png"
                with open(logoname, "wb") as file:
                    file.write(logoresponse.content)
if __name__ == '__main__':
    getlogo()

