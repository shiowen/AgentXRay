from enum import Enum

class RoleType(Enum):
    LEADER_ADD = "leader_add"
    LEADER_DELETE = "leader_delete"
    ACTOR = 'actor'
    CRITIC = 'critic'
    REVIEWER = 'reviewer'
    WORKFLOW = 'workflow'
    CODE = 'code'
    NON_CODE = 'non-code'
    TOOL = 'tool'

class TaskType(Enum):
    CODE = "Code"

class NodeType(Enum):
    AGENT = "agent"
    TOOL = "tool"
