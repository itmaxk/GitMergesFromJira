import gitlab
import gitlab.v4.objects
import requests
from bs4 import BeautifulSoup
import re
import configparser
import os
import colorama
from termcolor import colored

def createConfig(path):
    config = configparser.ConfigParser()
    config.add_section("Settings")
    config.set("Settings", "jiraLink", "")
    config.set("Settings", "jiraLogin", "")
    config.set("Settings", "jiraPass", "")
    config.set("Settings", "jiraParseURL", "")
    config.set("Settings", "gitLink", "")
    config.set("Settings", "gitToken", "")
    config.set("Settings", "gitImplementationProjectID", "")
    config.set("Settings", "targetBranch", "")
    config.set("Settings", "promoteBranch", "")
    config.set("Settings", "promoteBranchDate", "")
    config.set("Settings", "info", "Your current settings %(jiraLogin)s  %(jiraParseURL)s  %(gitLink)s  %(gitImplementationProjectID)s ")

    with open(path, "w") as config_file:
        config.write(config_file)

def crudConfig(path):
    if not os.path.exists(path):
        createConfig(path)

    config = configparser.ConfigParser()
    config.read(path)

    # jiraLogin = config.get("Settings", "jiraLogin")
    # jiraPass = config.get("Settings", "jiraPass")
    # jiraParseURL = config.get("Settings", "jiraParseURL")
    # gitLink = config.get("Settings", "gitLink")
    # gitToken = config.get("Settings", "gitToken")
    # gitImplementationProjectID = config.get("Settings", "gitImplementationProjectID")

    with open(path, "w") as config_file:
        config.write(config_file)

def get_config(path):
    config = configparser.ConfigParser()
    config.read(path)
    return config

def get_setting(path, section, setting):

    config = get_config(path)
    value = config.get(section, setting)
    msg = "{section} {setting} is {value}".format(
        section=section, setting=setting, value=value
    )
    #print(msg)
    return value


def get_html(site):
    r = requests.get(site+'?os_username='+jiraLogin+'&os_password='+jiraPass)
    return r.text

def get_links_a_with_site(soup_resp, class_tag):
    vLinksSite = []
    for link in soup_resp.find_all("a", {"class": class_tag}):
        vLinksSite.append(jiraLink+link.get('href'))
    return vLinksSite

def get_links_a(soup_resp, class_tag):
    vLinks = []
    for link in soup_resp.find_all("a", {"class": class_tag}):
        vLinks.append(link.get('href'))
    return vLinks

def get_links_from_task(vLinksTask):
    my_dict = {}
    tempList = []
    for link in vLinksTask:
        linkHTML = get_html(link)
        soupLinks = get_links_a((BeautifulSoup(linkHTML, 'html.parser')),"link-title")
        for s in soupLinks:
            if re.search(r'https://git', s) is not None:
               tempList.append(s)
        gitLinks = tempList.copy()
        my_dict[link] = gitLinks
        tempList.clear()
    return my_dict

def get_links_from_one_task(vLinksTask):
    my_dict = {}
    tempList = []
    linkHTML = get_html(vLinksTask)
    soupLinks = get_links_a((BeautifulSoup(linkHTML, 'html.parser')),"link-title")
    for s in soupLinks:
        if re.search(r'https://git', s) is not None:
            tempList.append(s)
    gitLinks = tempList.copy()
    my_dict[vLinksTask] = gitLinks
    tempList.clear()
    return my_dict

def get_git_mr_status(gitlab_link, token, git_project_id, my_dict):
    gl = gitlab.Gitlab(gitlab_link, private_token=token)
    # VSK - Project ID: 277
    project_id = git_project_id
    res = {}
    result = {}
    temp = {}
    mrlist = []
    tempmrlist = []
    for git_keys, git_values in my_dict.items():
        print('Собираем информацию: ' + git_keys)
        for git_v in git_values:
            git_link_id = re.search(r'\d{1,}$', git_v)
            project = gl.projects.get(project_id)
            if git_link_id == None:
                continue
            else:
                try:
                    mr = project.mergerequests.get(git_link_id[0])
                except gitlab.exceptions.GitlabGetError as e:
                    if e.response_code == 404:
                        break
                tempmrlist.append(mr.title)
                tempmrlist.append(mr.state)
                tempmrlist.append(mr.target_branch)
                tempmrlist.append(mr.merged_at)
            mrlist = tempmrlist.copy()
            temp[git_v]=mrlist
            res = temp.copy()
            tempmrlist.clear()
        result[git_keys]=res
        temp.clear()
    return result

def main():
    versionsHTML = get_html(jiraParseURL)
    soupVersions = BeautifulSoup(versionsHTML, 'html.parser')
    versionsLinks = get_links_a_with_site(soupVersions, "issue-summary")
    if re.search(r'browse', jiraParseURL) is not None:
        taskLinks = get_links_from_one_task(jiraParseURL)
    else:
        taskLinks = get_links_from_task(versionsLinks)
    status = get_git_mr_status(gitLink, gitToken, gitImplementationProjectID, taskLinks)
    for git_keys, git_values in status.items():
        print('\n' + colored('Merge requests status for: ', 'blue') + git_keys)
        targetBranchList = []
        promoteMessage = colored('Не попал с промоутом ' + promoteBranch + ' от: ' + promoteBranchDate, 'white', 'on_red');
        for git_k in git_values.items():
            if git_k[1][3] == None:
                continue
            print('\n' + git_k[1][0])
            if git_k[1][1] == 'merged':
                print('MR: ' + git_k[0], colored(git_k[1][1], 'green') + ' to ' + git_k[1][2] + ' (MR was merged at: ' + git_k[1][3] + ')')
            elif git_k[1][1] == 'closed' or git_k[1][1] == 'opened':
                print('MR: ' + git_k[0], colored(git_k[1][1], 'red') + ' to ' + git_k[1][2] + ' (MR was merged at: ' + git_k[1][3] + ')')
            else:
                print('MR: ' + git_k[0], git_k[1][1] + ' to ' + git_k[1][2] + ' (MR was merged at: ' + git_k[1][3] + ')')
            if git_k[1][2] == targetBranch:
                targetBranchList.append(targetBranch)
                if git_k[1][3] < promoteBranchDate:
                    print(colored('MR DATE: ' + git_k[1][3] + ' раньше указанной даты: ' + promoteBranchDate, 'white', 'on_red'))
                else:
                    print(colored('MR DATE: ' + git_k[1][3] + ' позже указанной даты: ' + promoteBranchDate, 'green'))

            if git_k[1][2] == promoteBranch and git_k[1][1] == 'merged' and git_k[1][3] < promoteBranchDate:
                promoteMessage = colored('MR попал в ' + targetBranch + ' после промоута ' + promoteBranch + ' от: ' + promoteBranchDate, 'magenta', 'on_green');
            #     print(colored('MR найден в ветке: ' + targetBranch, 'green'))
            # else:
            #     print(colored('MERGE REQUEST НЕ НАЙДЕН В ВЕТКЕ: ' + targetBranch, 'white', 'on_red'))
        if not targetBranchList:
            print('\n' + colored('MERGE REQUEST НЕ НАЙДЕН В ВЕТКЕ: ' + targetBranch, 'white', 'on_red'))
            print(promoteMessage)
        else:
            print(colored('MR найден в ветке: ' + targetBranch, 'green'))
        targetBranchList.clear()

        print('')
    input('Press ENTER to exit')

if __name__ == '__main__':
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    initfile = os.path.join(thisfolder, 'settings.ini')
    path = initfile
    jiraLink = get_setting(path, 'Settings', 'jiraLink')
    jiraLogin = get_setting(path, 'Settings', 'jiraLogin')
    jiraPass = get_setting(path, 'Settings', 'jiraPass')
    jiraParseURL = get_setting(path, 'Settings', 'jiraParseURL')
    gitLink = get_setting(path, 'Settings', 'gitLink')
    gitToken = get_setting(path, 'Settings', 'gitToken')
    gitImplementationProjectID = get_setting(path, 'Settings', 'gitImplementationProjectID')
    targetBranch = get_setting(path, 'Settings', 'targetBranch')
    promoteBranch = get_setting(path, 'Settings', 'promoteBranch')
    promoteBranchDate = get_setting(path, 'Settings', 'promoteBranchDate')
    colorama.init()
    main()
