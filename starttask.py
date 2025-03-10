import schedule
import time
import os
def playtask():
    current_time = time.strftime("%H:%M:%S", time.localtime())
    print("当前时间：", current_time)
    os.system("python3 /app/config/iptv.py")
def logotask():
    current_time = time.strftime("%H:%M:%S", time.localtime())
    print("当前时间：", current_time)
    os.system("python3 /app/config/getlogo.py")
if __name__ == "__main__":
    time1 = "01:00"  # 设置目标时间
    time2 = "13:00"
    time3 = "01:01"
    time4 = "13:01"
    #立即执行一次
    playtask()
    logotask()
    # 每天的1点执行任务
    schedule.every().day.at(time1).do(playtask)
    # 每天的13点执行任务
    schedule.every().day.at(time2).do(playtask)
    # 每天的1点01分执行任务
    schedule.every().day.at(time3).do(logotask)
     # 每天的13点01分执行任务
    schedule.every().day.at(time4).do(logotask)
    #根据自己需要可任意选择
    
    #每30秒执行一次
    #schedule.every(1).seconds.do(playtask)
    
    #每30分钟执行一次
    #schedule.every(30).minutes.do(playtask) 
    #每2小时执行一次
    #schedule.every(2).hours.do(playtask) 
    #每1小时的第十分钟执行一次
    #schedule.every(2).hoursat(':10').do(playtask) 
    # 每天的10:30执行任务
    #schedule.every().day.at("10:30").do(playtask) 
    # 每个月执行任务
    #schedule.every().monday.do(playtask)
    # 每分钟的第17秒执行任务
    #schedule.every().minute.at(":17").do(playtask)
   
    while True:
        schedule.run_pending()
        time.sleep(1)
