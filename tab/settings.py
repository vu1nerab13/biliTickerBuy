import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import gradio as gr
from loguru import logger

from config import main_request, get_application_tmp_path

buyer_value = []
addr_value = []
ticket_value = []
project_name = []
ticket_str_list = []


def filename_filter(filename):
    filename = re.sub('[\/:*?"<>|]', '', filename)
    return filename


def on_submit_ticket_id(num):
    global buyer_value
    global addr_value
    global ticket_value
    global project_name
    global ticket_str_list

    try:
        buyer_value = []
        addr_value = []
        ticket_value = []
        if "http" in num or "https" in num:
            num = extract_id_from_url(num)
            extracted_id_message = f"已提取URL票ID：{num}"
        else:
            return [
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(visible=False),
                gr.update(value='输入无效，请输入一个有效的网址。', visible=True),
            ]
        res = main_request.get(
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={num}&project_id={num}"
        )
        ret = res.json()
        logger.debug(ret)

        # 检查 errno
        if ret.get('errno') == 100001:
            return [
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(visible=True),
                gr.update(value='输入无效，请输入一个有效的票ID。', visible=True),
            ]
        elif ret.get('errno') != 0:
            return [
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(visible=True),
                gr.update(value=ret.get('msg', '未知错误') + '。', visible=True),
            ]

        data = ret["data"]
        ticket_str_list = []

        project_id = data["id"]
        project_name = data["name"]

        project_start_time = datetime.fromtimestamp(data["start_time"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        project_end_time = datetime.fromtimestamp(data["end_time"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        venue_info = data["venue_info"]
        venue_name = venue_info["name"]
        venue_address = venue_info["address_detail"]

        for screen in data["screen_list"]:
            screen_name = screen["name"]
            screen_id = screen["id"]
            for ticket in screen["ticket_list"]:
                ticket_desc = ticket["desc"]
                ticket_price = ticket["price"]
                ticket["screen"] = screen_name
                ticket["screen_id"] = screen_id
                ticket_can_buy = "可购买" if ticket["clickable"] else "无法购买"
                ticket_str = f"{screen_name} - {ticket_desc} - ￥{ticket_price / 100} - {ticket_can_buy}"
                ticket_str_list.append(ticket_str)
                ticket_value.append({"project_id": project_id, "ticket": ticket})

        buyer_json = main_request.get(
            url=f"https://show.bilibili.com/api/ticket/buyer/list?is_default&projectId={project_id}"
        ).json()
        logger.debug(buyer_json)
        addr_json = main_request.get(
            url="https://show.bilibili.com/api/ticket/addr/list"
        ).json()
        logger.debug(addr_json)

        buyer_value = buyer_json["data"]["list"]
        buyer_str_list = [
            f"{item['name']}-{item['personal_id']}" for item in buyer_value
        ]
        addr_value = addr_json["data"]["addr_list"]
        addr_str_list = [
            f"{item['addr']}-{item['name']}-{item['phone']}" for item in addr_value
        ]
        addr_str_list = ["地球"]

        return [
            gr.update(choices=ticket_str_list),
            gr.update(choices=buyer_str_list),
            gr.update(choices=buyer_str_list),
            gr.update(choices=addr_str_list),
            gr.update(visible=True),
            gr.update(
                value=f"{extracted_id_message}\n获取票信息成功:\n展会名称：{project_name}\n"
                      f"开展时间：{project_start_time} - {project_end_time}\n场馆地址：{venue_name} {venue_address}",
                visible=True,
            ),
        ]
    except Exception as e:
        return [
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(value=e, visible=True),
        ]


def extract_id_from_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get('id', [None])[0]


def on_submit_all(ticket_id, ticket_info, people_indices, people_buyer_index, address_index):
    try:
        # if ticket_number != len(people_indices):
        #     return gr.update(
        #         value="生成配置文件失败，保证选票数目和购买人数目一致", visible=True
        #     )
        ticket_cur = ticket_value[ticket_info]
        people_cur = [buyer_value[item] for item in people_indices]
        people_buyer_cur = buyer_value[people_buyer_index]
        ticket_id = extract_id_from_url(ticket_id)
        if ticket_id is None:
            return [gr.update(value="你所填不是网址，或者网址是错的", visible=True),
                    gr.update(value={}),
                    gr.update()]
        if str(ticket_id) != str(ticket_cur["project_id"]):
            return [gr.update(value="当前票信息已更改，请点击“获取票信息”按钮重新获取", visible=True),
                    gr.update(value={}),
                    gr.update()]
        if len(people_indices) == 0:
            return [gr.update(value="至少选一个实名人", visible=True),
                    gr.update(value={}),
                    gr.update()]
        address_cur = addr_value[address_index]
        detail = f'{project_name}-{ticket_str_list[ticket_info]}'
        for p in people_cur:
            detail += f"-{p['name']}"
        config_dir = {
            "detail": detail,
            "count": len(people_indices),
            "screen_id": ticket_cur["ticket"]["screen_id"],
            "project_id": ticket_cur["project_id"],
            "sku_id": ticket_cur["ticket"]["id"],
            "order_type": 1,
            "pay_money": ticket_cur["ticket"]["price"] * len(people_indices),
            "buyer_info": people_cur,
            "buyer": people_buyer_cur["name"],
            "tel": people_buyer_cur["tel"],
            "deliver_info": {
                "name": address_cur["name"],
                "tel": address_cur["phone"],
                "addr_id": address_cur["id"],
                "addr": address_cur["prov"]
                        + address_cur["city"]
                        + address_cur["area"]
                        + address_cur["addr"],
            },
        }
        filename = os.path.join(get_application_tmp_path(), filename_filter(detail) + ".json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_dir, f, ensure_ascii=False, indent=4)
        return [gr.update(), gr.update(value=config_dir, visible=True), gr.update(value=filename, visible=True)]
    except Exception as e:
        return [gr.update(value="生成错误，仔细看看你可能有哪里漏填的", visible=True), gr.update(value={}),
                gr.update()]


def setting_tab():
    gr.Markdown("""
> **必看**
>
> 保证自己在抢票前，已经配置了地址和购买人信息(就算不需要也要提前填写) 如果没填，生成表单时候不会出现任何选项
>
> - 地址 ： 会员购中心->地址管理
> - 购买人信息：会员购中心->购买人信息
""")
    info_ui = gr.TextArea(
        info="此窗口为输出信息", label="输出信息", interactive=False, visible=False
    )
    with gr.Column():
        ticket_id_ui = gr.Textbox(
            label="想要抢票的网址",
            interactive=True,
            info="例如：https://show.bilibili.com/platform/detail.html?id=84096",
        )
        ticket_id_btn = gr.Button("获取票信息")
        with gr.Column(visible=False) as inner:
            with gr.Row():
                people_ui = gr.CheckboxGroup(
                    label="身份证实名认证",
                    interactive=True,
                    type="index",
                    info="必填，选几个就代表买几个人的票，在哔哩哔哩客户端-会员购-个人中心-购票人信息中添加",
                )
                ticket_info_ui = gr.Dropdown(
                    label="选票",
                    interactive=True,
                    type="index",
                    info="必填，此处的「无法购买」仅代表当前状态",
                )
            with gr.Row():
                people_buyer_ui = gr.Dropdown(
                    label="联系人",
                    interactive=True,
                    type="index",
                    info="必填，如果候选项为空请到「购票人信息」添加",
                )
                address_ui = gr.Dropdown(
                    label="地址",
                    interactive=True,
                    type="index",
                    info="必填，如果候选项为空请到「地址管理」添加",
                )

            config_btn = gr.Button("生成配置")
            config_file_ui = gr.File(visible=False)
            config_output_ui = gr.JSON(
                label="生成配置文件（右上角复制）",
                visible=False,
            )
            config_btn.click(
                fn=on_submit_all,
                inputs=[
                    ticket_id_ui,
                    ticket_info_ui,
                    people_ui,
                    people_buyer_ui,
                    address_ui,
                ],
                outputs=[info_ui, config_output_ui, config_file_ui]
            )

        ticket_id_btn.click(
            fn=on_submit_ticket_id,
            inputs=ticket_id_ui,
            outputs=[
                ticket_info_ui,
                people_ui,
                people_buyer_ui,
                address_ui,
                inner,
                info_ui,
            ],
        )
