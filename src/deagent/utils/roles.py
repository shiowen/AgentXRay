import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def filter_role_profile(generated_content: str) -> Dict:
    rolebooks = {}
    if generated_content == "":
        logger.warning("Generated role profile content is empty")
        return None
    else:
        regex = r"```(.*?)\n(.*?)\n(.*?)\n```"
        matches = re.finditer(regex, generated_content, re.DOTALL)
        for match in matches:
            role_name = match.group(1)
            role_profile = match.group(2)
            role_type = match.group(3).lower()
            if role_name is not None and role_profile is not None and len(role_name) > 0 and len(role_profile) > 0:
                rolebooks[role_name] = {"role_profile":role_profile, "role_type":role_type}
    return rolebooks

def filter_workflow(generated_content: str) -> List:
    if generated_content == "":
        logger.warning("Generated workflow content is empty")
        return None
    else:
        regex = r'\d+(?:\s*->\s*\d+)*'
        matches = re.findall(regex, generated_content)
        number_sequences = [re.sub(r'\s*->\s*', ' ', match) for match in matches]
        number_lists = [list(map(int, seq.split())) for seq in number_sequences]
        return number_lists[-1]

def filter_delete_role_number(generated_content: str) -> List:
    if generated_content == "":
        logger.warning("Generated workflow content is empty")
        return None
    else:
        regex = r'<Agent(\d+)>'
        matches = re.findall(regex, generated_content)
        numbers = list(map(int, matches))
        return numbers


def role_team_generate(AgentList: List) -> str:
    current_team = ""
    for i in range(len(AgentList)):
        current_team += f"<Agent{i+1}>\n```{AgentList[i].get_role_name()}\n"
        current_team += AgentList[i].get_agent_profile()
        current_team += "\n"
        current_team += AgentList[i].get_role_type()
        current_team += "\n```\n"
    return current_team

def agent_list_convert_rolebooks(AgentList: List) -> Dict:
    rolebooks = {}
    for agent in AgentList:
        role_name = agent.get_role_name()
        role_profile = agent.get_agent_profile()
        role_type = agent.get_role_type()
        rolebooks[role_name] = {"role_profile":role_profile, "role_type":role_type}
    return rolebooks
