import requests, os
from peewee import *
import datetime
from init import ChaZuo, KongTiao
from toml import load
import pandas as pd


def get_df(equipmentInfoId):
    url = "http://10.128.13.25/feemanager/findSurplusElectricByMeterSearchPower.action"
    flag = False
    counter = 0
    while not flag:
        response = requests.request(
            "POST", url, data={"equipmentInfoId": equipmentInfoId}
        ).json()
        counter += 1
        if response.get("equipmentList"):
            flag = True
        if counter > 10:
            return None
    # print(response)
    equipmentList = response["equipmentList"]
    return {
        # 充值电量
        "surplus": float(equipmentList["roomSurplusBuyElecNum"]),
        # 赠送电量
        "give": float(equipmentList["roomSurplusGiveElecNum"]),
        # 总电量
        "total": float(equipmentList["roomSurplusBuyElecNum"])
        + float(equipmentList["roomSurplusGiveElecNum"]),
        # 按当前电压
        "voltage": equipmentList["line1Voltage"],
        # 当前电流
        "electricity": equipmentList["line1Electricity"],
    }


script_dir = os.path.dirname(os.path.abspath(__file__))

config = load(script_dir + "/config.toml")


def get_latest_db_data(model):
    # 查询数据库，按时间降序排列，获取第一条记录
    query = model.select().order_by(model.time.desc()).limit(1)
    df = pd.DataFrame(list(query.dicts()))

    # 将 'charge' 列转换为 float 类型
    if "charge" in df.columns:
        df["charge"] = df["charge"].astype(float)

    return df["charge"].values[0] if not df.empty else 0.0


def get_latest_data():
    try:
        print("获取数据...")
        chazuo_response = get_df(
            config["student"]["equipments"]["chazuo"]["equipmentInfoId"]
        )
        print("插座：", chazuo_response["total"])
        # 插座
        kongtiao_response = get_df(
            config["student"]["equipments"]["kongtiao"]["equipmentInfoId"]
        )
        print("空调：", kongtiao_response["total"])

        ChaZuo.create(charge=chazuo_response["total"], time=datetime.datetime.now())
        KongTiao.create(charge=kongtiao_response["total"], time=datetime.datetime.now())
    except Exception as e:
        print(e)
        print("获取数据失败，请检查 config 配置并重新初始化。")
        return {
            "status": 0,
            "chazuo": 0,
            "kongtiao": 0,
        }
        # 状态码，插座电量，空调电量

    return {
        "status": 1,
        "chazuo": chazuo_response["total"],
        "kongtiao": kongtiao_response["total"],
    }


def notify(chazuo_info, kongtiao_info):
    chazuo_threshold = config["notify"]["chazuo_threshold"]
    kongtiao_threshold = config["notify"]["kongtiao_threshold"]

    try:
        from BarkNotificator import BarkNotificator

        bark = BarkNotificator(device_token=config["notify"]["bark"]["device_token"])
    except ImportError:
        print("未安装 BarkNotificator")
        return

    if chazuo_info < chazuo_threshold:
        bark.send(
            title="插座电量不足",
            content=f"剩余 {chazuo_info:.2f} 度，请及时充电费！",
        )
    if kongtiao_info < kongtiao_threshold:
        bark.send(
            title="空调电量不足",
            content=f"剩余 {kongtiao_info:.2f} 度，请及时充电费！",
        )

    if chazuo_info - db_chazuo_info > 0:
        bark.send(title="插座", content=f"充入 {chazuo_info - db_chazuo_info:.2f} 度。")
    if kongtiao_info - db_kongtiao_info > 0:
        bark.send(
            title="空调",
            content=f"充入 {kongtiao_info - db_kongtiao_info:.2f} 度。",
        )


if __name__ == "__main__":

    # 获取距离现在最近的插座和空调数据
    db_chazuo_info = get_latest_db_data(ChaZuo)
    db_kongtiao_info = get_latest_db_data(KongTiao)

    print("插座 (latest)：", db_chazuo_info)
    print("空调 (latest)：", db_kongtiao_info)
    print()

    data = get_latest_data()
    if data["status"] == 0:
        exit(1)
    else:
        chazuo_info = data["chazuo"]
        kongtiao_info = data["kongtiao"]

    if config["notify"]["bark"]["enabled"]:
        notify(chazuo_info, kongtiao_info)

    # 返回值
