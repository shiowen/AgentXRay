# search/search.py -  + ablation tool pool

from deagent.search import MCTSNode, MCTS
from deagent.utils import output_path, logger
import os
try:
    import yaml
except ImportError:  # pragma: no cover - only used in minimal environments
    yaml = None


def mcts_search(train_data, iterations=20):
    """
    MCTS + 

    -  config.ablation.agent_only = true   AGENT_ONLY=1 -> 
    -  config.ablation.minimal_tcompilerool_pool = true   MINIMAL_TOOL_POOL=1 ->  minimal_tool_set
    - 

    New:
    -  CONFIG_PATH  config.yaml
    -  MCTS_BASELINE=1 MCTS baseline
    """
    from deagent.agents import NodeType, TaskType

    #  CONFIG_PATH
    project_root = os.path.dirname(os.path.dirname(__file__))
    default_cfg = os.path.join(project_root, 'config', 'config.yaml')
    config_path = os.environ.get('CONFIG_PATH', default_cfg)
    try:
        if yaml is None:
            config = {}
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
    except Exception:
        config = {}

    ablation_cfg = config.get('ablation', {})

    # True baseline: no tools regardless of config
    baseline_flag = os.environ.get('MCTS_BASELINE', '0') == '1'

    agent_only_flag = (
        baseline_flag or
        bool(ablation_cfg.get('agent_only', False)) or
        os.environ.get('AGENT_ONLY', '0') == '1'
    )

    minimal_pool_flag = (not agent_only_flag) and (
        bool(ablation_cfg.get('minimal_tool_pool', False)) or
        os.environ.get('MINIMAL_TOOL_POOL', '0') == '1'
    )

    minimal_tool_set = ablation_cfg.get('minimal_tool_set', [
        'syntax_error_checker',
        'undefined_name_checker',
        'dependency_extractor',
        'code_summarizer',
        'test_runner'
    ])

    # Agent
    root = MCTSNode(task_type=TaskType.CODE, type=NodeType.AGENT)

    full_tool_list = [
        'compiler',
        'empty_detect',
        'variable_checker',
        'undefined_name_checker',
        'syntax_error_checker',
        'style_checker',
        'dependency_extractor',
        'file_lister',
        'code_summarizer',
        'test_runner',
        'file_writer',
        'file_reader',
    ]

    if agent_only_flag:
        tool_list = []
        if baseline_flag:
            logger.info('[BASELINE] MCTS_BASELINE enabled: tool expansions disabled.')
        else:
            logger.info('[ABLATION] Agent-only mode enabled: tool expansions disabled.')
    elif minimal_pool_flag:
        tool_list = list(dict.fromkeys(minimal_tool_set))
        logger.info(f"[ABLATION] Minimal tool pool enabled: {tool_list}")
    else:
        tool_list = full_tool_list
        logger.info(f"[INFO] Using full tool list: {tool_list}")

    # MCTS
    mcts_path = os.path.join(output_path, 'mcts_tree.json')
    mcts = MCTS(root, train_data, tool_list)

    #  tool_list 
    if os.path.exists(mcts_path):
        try:
            mcts = mcts.load_tree_from_file(mcts_path, train_data, tool_list)
            logger.info(f"Loaded existing MCTS tree from {mcts_path}")
        except Exception as e:
            logger.warning(f"Failed to load existing tree: {e}\nStarting with new tree")

    best_workflow = mcts.search(iterations=iterations)

    try:
        logger.info("===== Best Workflow Selected =====")
        logger.info(f"Length: {len(best_workflow)}")
        for idx, n in enumerate(best_workflow, 1):
            ntype = 'Agent' if hasattr(n, 'is_agent') and n.is_agent() else ('Tool' if hasattr(n, 'is_tool') and n.is_tool() else 'Unknown')
            visits = getattr(n, 'visits', 0)
            q = (getattr(n, 'value', 0) / visits) if visits > 0 else 0.0
            data_obj = getattr(n, 'data', '')
            try:
                import json as _json
                if isinstance(data_obj, (dict, list)):
                    data_str = _json.dumps(data_obj, ensure_ascii=False)
                else:
                    data_str = str(data_obj)
            except Exception:
                data_str = str(data_obj)
            brief = data_str.replace('\n', ' ')
            logger.info(f"{idx}. [{ntype}] depth={getattr(n, 'depth', '-')}, visits={visits}, q={q:.3f}, data={brief}")
        logger.info("=================================")
    except Exception as e:
        logger.error(f"Failed to log best workflow: {e}")

    return best_workflow
