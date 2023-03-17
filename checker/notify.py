warn_ico = "⚠"
error_ico = "❌"
ok_ico = "✅"
question_ico = "❓"
host_ico = '🖥️'
service_ico = '⚙️'


def choose_icon(state):
    if state == 'UP':
        return ok_ico
    elif state == 'DOWN':
        return error_ico
    elif state == 'UNKNOWN':
        return question_ico
    elif state == 'OK':
        return ok_ico
    elif state == 'WARNING':
        return warn_ico
    elif state == 'CRITICAL':
        return error_ico
    else:
        raise Exception('No state to icon matched.')


def choose_color(state):
    if state == 'UP':
        return '#44bb77'
    elif state == 'DOWN':
        return '#ff5566'
    elif state == 'UNKNOWN':
        return '#aa44ff'
    elif state == 'OK':
        return '#44bb77'
    elif state == 'WARNING':
        return '#ffaa44'
    elif state == 'CRITICAL':
        return '#ff5566'
    else:
        raise Exception('No state to color matched.')


def newline_to_formatted_html(string):
    if '\n' in string:
        string = f'<br><pre>{string}</pre>'
    return string


def build_msg(host_name, host_display_name, state, date_str, output, service_name=None, service_display_name='', address='', comment='', author='', icinga2_url=''):
    if service_name:
        item = f'**{service_display_name}** on **{host_display_name}**'
        icon = service_ico
    else:
        item = f'**{host_display_name}**'
        icon = host_ico
    icon = f'{choose_icon(state)}&nbsp;&nbsp;{icon}'

    if address:
        address = f'<br>**IP:** {address}'
    if comment and author:
        comment = f'<br>**Comment by {author}:** {newline_to_formatted_html(comment)}'
    if icinga2_url:
        icinga2_url = icinga2_url.strip("/")
        if service_name:
            icinga2_url = f'<br>[Quick Link]({icinga2_url}/icingadb/service?name={service_name.replace(" ", "%20")}&host.name={host_name.replace(" ", "%20")})'
        elif host_name:
            icinga2_url = f'<br>[Quick Link]({icinga2_url}/icingadb/host?name={host_name.replace(" ", "+")})'

    msg = f"""{icon}&nbsp;&nbsp;&nbsp;{item} is **<font color="{choose_color(state)}">{state}</font>** <br>
**When:** {date_str}. <br>
**Info:** {newline_to_formatted_html(output)}{address}{comment}{icinga2_url}"""
    return msg
