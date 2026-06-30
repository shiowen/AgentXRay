"""
search/tree.py - 

"""
import math
import os
import time
import re  # 
from deagent.agents import NodeType, TaskType
from typing import List, Dict, Optional
from deagent.utils import logger, codes_to_content, output_path, filter_code
from .node_search import employee_search
import random
import json
try:
    import yaml
except ImportError:  # pragma: no cover - only used in minimal environments
    yaml = None

try:
    from deagent.evaluation import evaluate_similarity, evaluate_similarity_with_analysis
except ImportError as _evaluation_import_error:  # pragma: no cover - minimal env import support
    def evaluate_similarity(*args, **kwargs):
        raise RuntimeError(
            "Evaluation dependencies are not installed. Install requirements.txt "
            "before running MCTS search."
        ) from _evaluation_import_error

    def evaluate_similarity_with_analysis(*args, **kwargs):
        raise RuntimeError(
            "Evaluation dependencies are not installed. Install requirements.txt "
            "before running MCTS search."
        ) from _evaluation_import_error

try:
    from deagent.problem_analysis.problem_types import ProblemList
    from deagent.problem_analysis.text_parser import parse_evaluation_output
    from deagent.potential import AgentPotentialCalculator, PotentialScore
    ENHANCEMENT_MODULES_AVAILABLE = True
except ImportError as e:
    ENHANCEMENT_MODULES_AVAILABLE = False

file_path = os.path.dirname(__file__)
project_path = os.path.dirname(file_path)

_default_cfg = os.path.join(project_path, 'config', 'config.yaml')
_config_path = os.environ.get('CONFIG_PATH', _default_cfg)
try:
    if yaml is None:
        config = {}
    else:
        with open(_config_path, "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
except Exception as exc:
    logger.warning("Failed to load config from %s: %s", _config_path, exc)
    config = {}

mcts_tree_config = config.get('mcts_tree', {}) or {}

ENABLE_COLORING = mcts_tree_config.get('enable_coloring', True)

# Agent
AGENT_ONLY_MODE = False
try:
    AGENT_ONLY_MODE = (
        bool(config.get('ablation', {}).get('agent_only', False)) or
        os.environ.get('AGENT_ONLY', '0') == '1'
    )
except Exception:
    pass

PURE_RANDOM_MODE = os.environ.get('PURE_RANDOM', '0') == '1'
PURE_RANDOM_FORCED_MODEL = (
    os.environ.get('PURE_RANDOM_FORCED_MODEL')
    or os.environ.get('DEAGENT_DEFAULT_MODEL')
    or 'gpt-3.5-turbo'
)
if PURE_RANDOM_MODE:
    logger.info(' PURE_RANDOM_MODE enabled: training will ignore UCB and pick random children/expansions.')

MAX_CHILDREN_NUMBER = mcts_tree_config.get('max_child_number', 10)
MAX_DEPTH = mcts_tree_config.get('max_depth', 10)
NEW_UCB_WEIGHT = mcts_tree_config.get('new_ucb_weight', 10)
BETA = mcts_tree_config.get('beta', 0.5)

# Minimum desired workflow length when selecting the final workflow
MIN_WORKFLOW_LENGTH = 2

# === Agent/Tool  ===
MIN_AGENT_RATIO = mcts_tree_config.get('min_agent_ratio', 0.5)  # Agent
MAX_TOOLS_PER_NODE_DEFAULT = 6
MAX_TOOLS_PER_NODE = mcts_tree_config.get('max_tools_per_node', MAX_TOOLS_PER_NODE_DEFAULT)
SIM_AGENT_BIAS = mcts_tree_config.get('sim_agent_bias', 0.7)  # Agent

ROLLOUT_PENALTY_CONFIG = {
    'no_code_penalty': 0,        # 
    'empty_response_penalty': 0,  # 
    'error_response_penalty': 0,  # 
    'enable_penalty_logging': True,  # 
    'min_code_length': 10           # 
}

try:
    # Prefer config value: dynamic_selection.model_library_path
    rel_path = config.get('dynamic_selection', {}).get('model_library_path', 'config/model_library.json')
    _model_library_path = rel_path
    if not os.path.isabs(_model_library_path):
        _model_library_path = os.path.join(project_path, _model_library_path)

    with open(_model_library_path, 'r', encoding='utf-8') as _f:
        _model_library = json.load(_f)
    ALLOWED_MODELS = {m.get('name') for m in _model_library.get('models', []) if m.get('name')}
except Exception as e:
    logger.warning(f"Failed to load model library from config path: {e}")
    # Backward-compatible fallback (previous hard-coded default)
    try:
        _fallback_path = os.path.join(project_path, 'config', 'model_library.json')
        with open(_fallback_path, 'r', encoding='utf-8') as _f:
            _model_library = json.load(_f)
        ALLOWED_MODELS = {m.get('name') for m in _model_library.get('models', []) if m.get('name')}
    except Exception as _e2:
        logger.warning(f"Failed to load model_library.json fallback: {_e2}")
        ALLOWED_MODELS = set()

_env_allowed_models = {
    item.strip()
    for item in os.environ.get('DEAGENT_ALLOWED_MODELS', '').split(',')
    if item.strip()
}
if _env_allowed_models:
    ALLOWED_MODELS = ALLOWED_MODELS.intersection(_env_allowed_models) if ALLOWED_MODELS else _env_allowed_models

DEFAULT_MODEL = (
    os.environ.get('DEAGENT_DEFAULT_MODEL')
    or config.get('dynamic_selection', {}).get('fallback', {}).get('default_model')
    or 'gpt-3.5-turbo'
)


ENHANCEMENT_CONFIG = {
    'enable_potential_enhancement': True,
    'enhancement_weight': 0.3,
    'normalization_factor': 2.0,
    'similarity_threshold': 0.5,
    'min_confidence_threshold': 0.1,
    'debug_mode': False,  # False
    'performance_monitoring': True
}

class MCTSNode:
    """MCTS - """
    
    def __init__(self, task_type: TaskType, type: NodeType, parent=None, depth=0, model_name=None):
        self.parent: 'MCTSNode' = parent
        self.depth = depth
        self.type = type
        self.task_type = task_type
        self.model_name = model_name or DEFAULT_MODEL
        self.data = None
        self.content = ""
        self.terminal = False
        self.expanded = False
        self.children: List['MCTSNode'] = []
        self.visits = 0
        self.value = 0
        self.color = ""
        
        if ENHANCEMENT_MODULES_AVAILABLE:
            self.current_problems: Optional[ProblemList] = None
            self.evaluation_text: str = ""
            self.evaluation_score: float = 0.0
            self.potential_score: Optional[PotentialScore] = None
            self.ucb_enhancement_history: List[Dict] = []
            self.last_potential_calculation_time: float = 0.0
            self.selection_count = 0
            self.potential_calculation_time = 0.0
            self.ucb_calculation_time = 0.0

    def is_agent(self):
        return self.type == NodeType.AGENT

    def is_tool(self):
        return self.type == NodeType.TOOL
    
    def is_terminal(self):
        return self.terminal

    def is_fully_expanded(self):
        return len(self.children) == MAX_CHILDREN_NUMBER
    
    def is_leaf_node(self):
        return len(self.children) == 0
    
    def add_child(self, child):
        self.children.append(child)
    
    def update_evaluation_results(self, evaluation_score: float, evaluation_text: str = ""):
        """"""
        if not ENHANCEMENT_MODULES_AVAILABLE:
            return
            
        self.evaluation_score = evaluation_score
        self.evaluation_text = evaluation_text
        
        if evaluation_text:
            try:
                self.current_problems = parse_evaluation_output(evaluation_score, evaluation_text)
                if ENHANCEMENT_CONFIG['debug_mode']:
                    logger.info(f"Parsed {len(self.current_problems.problems)} problems from evaluation")
            except Exception as e:
                if ENHANCEMENT_CONFIG['debug_mode']:
                    logger.warning(f"Failed to parse problems: {e}")
                self.current_problems = None
    
    def calculate_potential_score(self, potential_calculator):
        """"""
        if not ENHANCEMENT_MODULES_AVAILABLE or not self.data or not hasattr(self, 'current_problems'):
            return None
        
        if not self.current_problems:
            return None
            
        try:
            start_time = time.time()
            potential_score = potential_calculator.calculate_agent_potential(
                self.data, self.current_problems
            )
            calculation_time = time.time() - start_time
            
            if hasattr(self, 'potential_calculation_time'):
                self.potential_calculation_time += calculation_time
                self.last_potential_calculation_time = calculation_time
            
            self.potential_score = potential_score
            return potential_score
            
        except Exception as e:
            if ENHANCEMENT_CONFIG['debug_mode']:
                logger.error(f"Potential calculation failed: {e}")
            return None
    
    def best_child_for_train(self, task, tool_list, c_param=1.4, potential_calculator=None):
        """ - """
        # === UCB /  ===
        if PURE_RANDOM_MODE:
            #  1  Agent 
            if self.color == 'black' and not self.is_fully_expanded() and not self.children:
                #  employee_search UnboundLocalError
                agent_list = employee_search(task, self.children, 1)
                if agent_list:
                    random_agent = random.choice(agent_list)
                    new_child = MCTSNode(task_type=self.task_type, type=NodeType.AGENT, parent=self, depth=self.depth+1)
                    new_child.data = random_agent
                    if new_child.depth >= MAX_DEPTH:
                        new_child.terminal = True
                    self.add_child(new_child)
                    return new_child
            if self.children:
                return random.choice(self.children)
            return self  # 
        # === Agent ===
        if not self.is_fully_expanded() and self.color == "black":
            #  PURE_RANDOM_MODE  UnboundLocalError
            # from deagent.search.node_search import employee_search  # <-- removed

            # Agent/Tool
            num_agents = sum(1 for c in self.children if c.is_agent())
            num_tools = sum(1 for c in self.children if c.is_tool())

            # Agent
            desired_agent_quota = max(1, int(MAX_CHILDREN_NUMBER * MIN_AGENT_RATIO))
            tool_quota = min(MAX_CHILDREN_NUMBER - desired_agent_quota, MAX_TOOLS_PER_NODE)
            tool_quota = max(0, tool_quota)
            if AGENT_ONLY_MODE:
                tool_quota = 0

            # Agent
            target_for_generation = max(1, desired_agent_quota)
            agent_list = employee_search(task, self.children, target_for_generation)

            available_tools = [t for t in tool_list if all(ch.data != t for ch in self.children)]
            if AGENT_ONLY_MODE:
                available_tools = []

            #  1Agent
            has_agent_child = any(child.is_agent() for child in self.children)
            if (not has_agent_child) and agent_list:
                random_agent = random.choice(agent_list)
                new_child = MCTSNode(task_type=self.task_type, type=NodeType.AGENT, 
                                     parent=self, depth=self.depth+1)
                new_child.data = random_agent
                if new_child.depth == MAX_DEPTH:
                    new_child.terminal = True
                if ENHANCEMENT_MODULES_AVAILABLE and hasattr(self, 'current_problems'):
                    if self.current_problems:
                        new_child.current_problems = self.current_problems
                        new_child.evaluation_text = getattr(self, 'evaluation_text', '')
                        new_child.evaluation_score = getattr(self, 'evaluation_score', 0.0)
                self.add_child(new_child)
                return new_child

            # Agent
            if has_agent_child and num_tools == 0 and available_tools and len(self.children) < MAX_CHILDREN_NUMBER and tool_quota > 0:
                # Agent available_tools   tool_quota=0
                random_tool = random.choice(available_tools)
                new_child = MCTSNode(task_type=self.task_type, type=NodeType.TOOL,
                                     parent=self, depth=self.depth+1)
                new_child.data = random_tool
                if new_child.depth == MAX_DEPTH:
                    new_child.terminal = True
                self.add_child(new_child)
                return new_child

            #  2Agent
            if num_agents < desired_agent_quota and agent_list:
                random_agent = random.choice(agent_list)
                new_child = MCTSNode(task_type=self.task_type, type=NodeType.AGENT, 
                                     parent=self, depth=self.depth+1)
                new_child.data = random_agent
                if new_child.depth == MAX_DEPTH:
                    new_child.terminal = True
                if ENHANCEMENT_MODULES_AVAILABLE and hasattr(self, 'current_problems'):
                    if self.current_problems:
                        new_child.current_problems = self.current_problems
                        new_child.evaluation_text = getattr(self, 'evaluation_text', '')
                        new_child.evaluation_score = getattr(self, 'evaluation_score', 0.0)
                self.add_child(new_child)
                return new_child

            #  3
            if num_tools < tool_quota and available_tools:
                # Agent
                random_tool = random.choice(available_tools)
                new_child = MCTSNode(task_type=self.task_type, type=NodeType.TOOL, 
                                     parent=self, depth=self.depth+1)
                new_child.data = random_tool
                if new_child.depth == MAX_DEPTH:
                    new_child.terminal = True
                self.add_child(new_child)
                return new_child

            #  4Agent
            if agent_list and len(self.children) < MAX_CHILDREN_NUMBER:
                random_agent = random.choice(agent_list)
                new_child = MCTSNode(task_type=self.task_type, type=NodeType.AGENT, 
                                     parent=self, depth=self.depth+1)
                new_child.data = random_agent
                if new_child.depth == MAX_DEPTH:
                    new_child.terminal = True
                if ENHANCEMENT_MODULES_AVAILABLE and hasattr(self, 'current_problems'):
                    if self.current_problems:
                        new_child.current_problems = self.current_problems
                        new_child.evaluation_text = getattr(self, 'evaluation_text', '')
                        new_child.evaluation_score = getattr(self, 'evaluation_score', 0.0)
                self.add_child(new_child)
                return new_child

            #  5Agent
            if available_tools and len(self.children) < MAX_CHILDREN_NUMBER:
                # Agent
                random_tool = random.choice(available_tools)
                new_child = MCTSNode(task_type=self.task_type, type=NodeType.TOOL, 
                                     parent=self, depth=self.depth+1)
                new_child.data = random_tool
                if new_child.depth == MAX_DEPTH:
                    new_child.terminal = True
                self.add_child(new_child)
                return new_child
        
        # === UCB ===
        if ENHANCEMENT_MODULES_AVAILABLE and ENHANCEMENT_CONFIG['enable_potential_enhancement']:
            return self._enhanced_child_selection(task, tool_list, c_param, potential_calculator)
        else:
            # UCB
            return self._basic_child_selection(c_param)



    def _enhanced_child_selection(self, task, tool_list, c_param, potential_calculator):
        """"""
        enhanced_ucb_scores = []
        
        for child in self.children:
            # UCB
            if child.visits == 0:
                original_ucb = float('inf')
            else:
                exploitation = child.value / child.visits
                exploration = c_param * math.sqrt((2 * math.log(self.visits) / child.visits))
                original_ucb = exploitation + exploration
            
            potential_boost = 0.0
            if (potential_calculator and 
                hasattr(child, 'current_problems') and child.current_problems and child.data):
                
                try:
                    potential_score = child.calculate_potential_score(potential_calculator)
                    if potential_score and potential_score.confidence >= ENHANCEMENT_CONFIG['min_confidence_threshold']:
                        potential_boost = (potential_score.overall_potential * 
                                         potential_score.confidence * 
                                         ENHANCEMENT_CONFIG['normalization_factor'])
                except Exception as e:
                    if ENHANCEMENT_CONFIG['debug_mode']:
                        logger.warning(f"Potential calculation failed: {e}")
            
            # UCB
            enhanced_ucb = original_ucb + ENHANCEMENT_CONFIG['enhancement_weight'] * potential_boost
            
            enhanced_ucb_scores.append({
                'child': child,
                'enhanced_ucb': enhanced_ucb,
                'potential_boost': potential_boost
            })
        
        if not enhanced_ucb_scores:
            return None
        
        best_result = max(enhanced_ucb_scores, key=lambda x: x['enhanced_ucb'])
        best_child = best_result['child']
        
        if hasattr(best_child, 'selection_count'):
            best_child.selection_count += 1
        
        return best_child
    
    def _basic_child_selection(self, c_param):
        """UCB"""
        choices_weights = [
            (child.value / child.visits) + c_param * math.sqrt((2 * math.log(self.visits) / child.visits))
            for child in self.children
        ]
        return self.children[choices_weights.index(max(choices_weights))]
    
    def best_child_for_eval(self, c_param=1.4):
        """ - """
        if not self.children:
            return None
        # Prefer children that have been visited (expanded/evaluated)
        visited_children = [c for c in self.children if c.visits > 0]
        if visited_children:
            # Pure exploitation: value/visits
            best_child = max(visited_children, key=lambda c: (c.value / c.visits))
            return best_child
        # Fallback: if no visited children, avoid picking unexpanded leaves during evaluation
        # Return None so caller can handle extension/fallback.
        return None
    
    def is_expanded(self):
        return self.expanded
    
    def update(self, value):
        self.visits += 1
        self.value += value

    def action(self, task, content):
        """"""
        if self.type == NodeType.AGENT:
            # Agent
            selected_model = self._extract_model_from_profile(self.data)
            reasoning_pattern = self._extract_reasoning_from_profile(self.data)
            
            logger.info(f"Agent using model: {selected_model}, reasoning: {reasoning_pattern}")
            
            from deagent.agents import EmployeeAgent
            employee = EmployeeAgent(self.task_type, self.data, selected_model)
            response = employee.query_gpt(task, content)
            self.content = response
            return response
            
        elif self.type == NodeType.TOOL:
            try:
                from deagent.agents import ToolAgent
                tool = ToolAgent(self.task_type, self.data)
                response = tool.query(content)

                if response is False:
                    logger.info(f"Tool {self.data} produced no actionable output; passing through content")
                    self.content = content
                    return content
                
                self.content = response
                return response
                
            except Exception as e:
                error_msg = f"Tool execution error: {str(e)}"
                logger.error(error_msg)
                return False
        
        return False
    
    def _extract_model_from_profile(self, profile):
        """agent profile + """
        #  gpt-4profilefallback
        if PURE_RANDOM_MODE:
            forced_model = PURE_RANDOM_FORCED_MODEL
            if forced_model not in ALLOWED_MODELS and ALLOWED_MODELS:
                logger.warning(f"PURE_RANDOM_MODE: forcing model '{forced_model}' not in ALLOWED_MODELS list.")
            else:
                logger.info(f"PURE_RANDOM_MODE: forcing model selection -> {forced_model}")
            return forced_model

        if not profile:
            logger.warning("Empty profile; using default model")
            return DEFAULT_MODEL

        # --- Robust parsing for duplicate fields ---
        # Some profiles contain both:
        #   Model: gpt-4-0125-preview
        #   Model:gpt-3.5-turbo
        # Prefer the *last* valid occurrence.
        def _clean(v: str) -> str:
            v = (v or "").strip()
            if v.startswith('[') and v.endswith(']'):
                v = v[1:-1].strip()
            v = re.sub(r"[\[\]`\*\"]", "", v).strip()
            v = v.split('|')[0].strip()
            v = v.split('#')[0].strip()
            return v

        # 1) Collect candidates in order, then take the last
        candidates = []

        # **Selected Model**: xxx (can appear in planner outputs)
        for m in re.finditer(r"\*\*Selected Model\*\*\s*:\s*([^\n]+)", profile, re.IGNORECASE):
            candidates.append(_clean(m.group(1)))

        # Selected Model: xxx
        for m in re.finditer(r"^\s*Selected Model\s*:\s*([^\n]+)", profile, re.IGNORECASE | re.MULTILINE):
            candidates.append(_clean(m.group(1)))

        # Model: xxx or Model:xxx (tolerate missing space)
        for m in re.finditer(r"^\s*Model\s*:\s*([^\n]+)", profile, re.IGNORECASE | re.MULTILINE):
            candidates.append(_clean(m.group(1)))

        # Remove empties
        candidates = [c for c in candidates if c]

        candidate = candidates[-1] if candidates else None

        if candidate:
            if ALLOWED_MODELS and candidate not in ALLOWED_MODELS:
                logger.warning(f"Model '{candidate}' not allowed; falling back to '{DEFAULT_MODEL}'")
                return DEFAULT_MODEL

            logger.info(f"Extracted model from profile: {candidate}")
            return candidate

        logger.warning("No model selection found; using default")
        return DEFAULT_MODEL
    
    def _extract_reasoning_from_profile(self, profile):
        """agent profile + fallback"""
        if PURE_RANDOM_MODE:
            logger.info("PURE_RANDOM_MODE: forcing reasoning pattern -> planning")
            return "planning"

        default_reasoning = config.get('dynamic_selection', {}).get('fallback', {}).get('default_reasoning', 'reasoning')

        # Load allowed patterns from config.yaml -> dynamic_selection.reasoning_patterns_path
        allowed_patterns = None
        try:
            rel_path = (config.get('dynamic_selection', {}) or {}).get('reasoning_patterns_path', 'config/reasoning_patterns.json')
            patterns_path = rel_path if os.path.isabs(rel_path) else os.path.join(project_path, rel_path)
            with open(patterns_path, 'r', encoding='utf-8') as handle:
                patterns_json = json.load(handle) or {}
            patterns = patterns_json.get('patterns', []) or []
            allowed_patterns = {p.get('name') for p in patterns if isinstance(p, dict) and p.get('name')}
        except Exception as e:
            logger.debug(f"Failed to load reasoning patterns list for validation: {e}")
            allowed_patterns = None

        if not profile:
            if allowed_patterns and default_reasoning not in allowed_patterns:
                return sorted(allowed_patterns)[0]
            return default_reasoning

        # Find Reasoning:xxx (take last occurrence for robustness)
        matches = re.findall(r'^\s*Reasoning\s*:\s*([^\n]+)$', profile, flags=re.IGNORECASE | re.MULTILINE)
        reasoning_pattern = matches[-1].strip() if matches else ""

        if not reasoning_pattern:
            logger.warning("No reasoning pattern found in profile, using default")
            if allowed_patterns and default_reasoning not in allowed_patterns:
                return sorted(allowed_patterns)[0]
            return default_reasoning

        # Normalize
        reasoning_pattern = re.sub(r"[\[\]`\*\"]", "", reasoning_pattern).strip()
        reasoning_pattern = reasoning_pattern.split('|')[0].strip()
        reasoning_pattern = reasoning_pattern.split('#')[0].strip()

        if allowed_patterns and reasoning_pattern not in allowed_patterns:
            logger.warning(f"Reasoning '{reasoning_pattern}' not allowed; falling back")
            if default_reasoning in allowed_patterns:
                return default_reasoning
            return sorted(allowed_patterns)[0]

        logger.info(f"Extracted reasoning pattern from profile: {reasoning_pattern}")
        return reasoning_pattern
    
    def to_dict(self):
        """ + """
        base_dict = {
            "data": self.data,
            "model_name": self.model_name,
            "value": self.value,
            "visits": self.visits,
            "task_type": self.task_type.name,
            "terminal": self.terminal,
            "expanded": self.expanded,
            "depth": self.depth,
            "type": self.type.name,
            "children": [child.to_dict() for child in self.children],
        }
        
        if ENHANCEMENT_MODULES_AVAILABLE and hasattr(self, 'evaluation_score'):
            base_dict["enhancement_data"] = {
                "evaluation_score": self.evaluation_score,
                "has_problems": hasattr(self, 'current_problems') and self.current_problems is not None,
                "problem_count": len(self.current_problems.problems) if hasattr(self, 'current_problems') and self.current_problems else 0
            }
        
        return base_dict

    @staticmethod
    def from_dict(data, parent=None):
        """"""
        node = MCTSNode(
            task_type=TaskType[data["task_type"]],
            type=NodeType[data["type"]],
            parent=parent,
            depth=data["depth"],
        )
        node.data = data["data"]
        node.model_name = data["model_name"]
        node.value = data["value"]
        node.visits = data["visits"]
        node.terminal = data["terminal"]
        node.expanded = data["expanded"]
        
        if "enhancement_data" in data and ENHANCEMENT_MODULES_AVAILABLE:
            enhancement_data = data["enhancement_data"]
            node.evaluation_score = enhancement_data.get("evaluation_score", 0.0)
        
        node.children = [MCTSNode.from_dict(child, parent=node) for child in data.get("children", [])]
        return node

def enhanced_code_quality_check(response, output_code):
    """"""
    penalties = []
    
    if not output_code or len(output_code) == 0:
        penalties.append(('no_code', ROLLOUT_PENALTY_CONFIG['no_code_penalty']))
        return penalties
    
    total_code_length = sum(len(code_content) for code_content in output_code.values())
    if total_code_length < ROLLOUT_PENALTY_CONFIG['min_code_length']:
        penalties.append(('insufficient_code', ROLLOUT_PENALTY_CONFIG['no_code_penalty'] * 0.5))
    
    code_text = ' '.join(output_code.values())
    if not any(keyword in code_text for keyword in ['def ', 'class ', 'function', 'import', 'from']):
        penalties.append(('no_programming_structure', ROLLOUT_PENALTY_CONFIG['no_code_penalty'] * 0.3))
    
    return penalties



class MCTS:
    """MCTS - """
    
    def __init__(self, root: MCTSNode, train_data: List[Dict], tool_list: List[str]):
        self.root = root
        self.train_data = train_data
        self.tool_list = tool_list
        
        if ENHANCEMENT_MODULES_AVAILABLE:
            try:
                self.potential_calculator = AgentPotentialCalculator()
                self.enhancement_statistics = {
                    'total_potential_calculations': 0,
                    'successful_problem_parsing': 0,
                    'failed_problem_parsing': 0,
                    'average_calculation_time': 0.0
                }
                logger.info("Enhanced MCTS initialized with problem-solving capabilities")
            except Exception as e:
                logger.warning(f"Failed to initialize enhancement components: {e}")
                self.potential_calculator = None
                self.enhancement_statistics = None
        else:
            self.potential_calculator = None
            self.enhancement_statistics = None

        self.current_iter = -1  #  simulation 

    def search(self, iterations=1000):
        """"""
        from deagent.utils import usage_stats
        for iteration in range(iterations):
            self.current_iter = iteration
            iter_usage_snap = usage_stats.snapshot()  #  token 
            logger.info(f"Iteration: {iteration}")         
            node = self.root
            
            if not self.train_data:
                logger.warning("No training data available")
                break
            
            data_index = iteration % len(self.train_data)  # 
            task = self.train_data[data_index].get("input", "")

            # 1) : sample["output"]["code_files"]
            # 2) gpt_* : sample["output"] 
            ground_truth_code = ""
            try:
                out_obj = self.train_data[data_index].get("output")
                if isinstance(out_obj, dict):
                    code_files = out_obj.get("code_files", {})
                    ground_truth_code = codes_to_content(code_files)
                elif isinstance(out_obj, str):
                    ground_truth_code = out_obj
                else:
                    ground_truth_code = ""
            except Exception:
                ground_truth_code = ""

            self.color_tree()
            
            while not node.is_terminal():      
                child_node = node.best_child_for_train(
                    task, 
                    tool_list=self.tool_list,
                    potential_calculator=self.potential_calculator
                )
                if child_node is None:
                    logger.warning("No selectable child node; stopping this search iteration")
                    reward = 0
                    break
                
                content = node.content
                response = child_node.action(task, content)
                
                if response is False:
                    child_node.terminal = True
                    reward = 0
                    node = child_node
                    break
                
                child_node.content = response
                
                if ENHANCEMENT_MODULES_AVAILABLE and response:
                    try:
                        evaluation_score, evaluation_text = evaluate_similarity_with_analysis(
                            response, ground_truth_code
                        )
                        child_node.update_evaluation_results(evaluation_score, evaluation_text)
                        
                        if hasattr(child_node, 'current_problems') and child_node.current_problems:
                            self.enhancement_statistics['successful_problem_parsing'] += 1
                        else:
                            self.enhancement_statistics['failed_problem_parsing'] += 1
                            
                    except Exception as e:
                        logger.warning(f"Enhanced evaluation failed, using basic: {e}")
                        evaluation_score = evaluate_similarity(response, ground_truth_code)
                        if hasattr(child_node, 'update_evaluation_results'):
                            child_node.update_evaluation_results(evaluation_score)
                else:
                    evaluation_score = evaluate_similarity(response, ground_truth_code)
                    if hasattr(child_node, 'update_evaluation_results'):
                        child_node.update_evaluation_results(evaluation_score)
                
                if not child_node.is_expanded():
                    logger.info("Simulation Stage Start")
                    reward = self.simulation(child_node, task, ground_truth_code)
                    logger.info(f"Simulation Stage End-Reward:{reward}")
                    node = child_node
                    break
                
                output_code = filter_code(response)
                output_code_str = codes_to_content(output_code)
                reward = evaluate_similarity(output_code_str, ground_truth_code)
                
                if reward > 0.8:
                    node = child_node
                    break
                    
                node = child_node
            
            self.backup(node, reward)
            logger.info("MCTS Tree Start")
            self.print_mcts_tree()
            self.save_tree_to_file(os.path.join(output_path, "mcts_tree.json"))
            logger.info("MCTS Tree End")

            try:
                # GT
                model_output_text = getattr(node, 'content', '') or ''
                ground_truth_text = ground_truth_code if 'ground_truth_code' in locals() else ''
                from deagent.evaluation import parse_code_content_to_files
                p1_files = parse_code_content_to_files(model_output_text)
                p2_files = parse_code_content_to_files(ground_truth_text)
                p1_cnt = len(p1_files) if p1_files else 0
                p2_cnt = len(p2_files) if p2_files else 0
                mode = 'static' if (p1_cnt > 0 and p2_cnt > 0) else 'cosine'
                # reward  no_code_penalty  simulation 
                try:
                    r_str = f"{float(reward):.3f}"
                except Exception:
                    r_str = str(reward)
                logger.info(f"[ITER_SIM] iter={iteration} reward={r_str} files(P1,P2)={p1_cnt},{p2_cnt} mode={mode}")
            except Exception as e:
                logger.warning(f"[ITER_SIM] iter={iteration} logging failed: {e}")

            # =====  token usage =====
            try:
                dp, dc, dt = usage_stats.delta_since(iter_usage_snap)
                logger.info(f"[ITER_USAGE] iter={iteration} prompt_tokens={dp} completion_tokens={dc} total_tokens={dt}")
            except Exception as e:
                logger.warning(f"[ITER_USAGE] iter={iteration} logging failed: {e}")

        return self.best_workflow()
    
# search/tree.py  MCTS 

    def simulation(self, node: MCTSNode, task, ground_truth_code):
        """ - Agent"""
        curr_node = node
        score = 0
        # has_generated_code = False  # 

        # --- Agent ---
        temp_node = curr_node
        final_content = temp_node.content  # 

        tools_used = 0
        # Agent
        agents_used = 0
        tool_quota = min(MAX_TOOLS_PER_NODE, max(0, MAX_CHILDREN_NUMBER - int(MAX_CHILDREN_NUMBER * MIN_AGENT_RATIO)))

        while not temp_node.is_terminal():
            complete_tool_list = [t for t in self.tool_list if all(ch.data != t for ch in temp_node.children)]
            if AGENT_ONLY_MODE:
                complete_tool_list = []

            # Agent
            target_for_generation = max(1, int(MAX_CHILDREN_NUMBER * MIN_AGENT_RATIO))
            agent_list = employee_search(task, temp_node.children, target_for_generation)

            if not agent_list and (not complete_tool_list or tools_used >= tool_quota):
                break

            # - Agent
            # - SIM_AGENT_BIASrolloutAgent
            next_is_tool = False
            if AGENT_ONLY_MODE:
                next_is_tool = False
            elif agents_used == 0:
                next_is_tool = False
            else:
                can_pick_tool = (tools_used < tool_quota) and bool(complete_tool_list)
                if can_pick_tool:
                    p_tool = max(0.05, 1.0 - SIM_AGENT_BIAS)
                    # Agent
                    total_steps = max(1, agents_used + tools_used)
                    current_agent_ratio = agents_used / total_steps
                    if current_agent_ratio >= MIN_AGENT_RATIO:
                        p_tool = min(0.9, p_tool + 0.2)
                    else:
                        p_tool = max(0.05, p_tool - 0.1)
                    next_is_tool = (random.random() < p_tool)
                else:
                    next_is_tool = False

            if next_is_tool:
                random_tool = random.choice(complete_tool_list)
                next_node = MCTSNode(temp_node.task_type, NodeType.TOOL, temp_node, temp_node.depth+1)
                next_node.data = random_tool
                tools_used += 1
            else:
                if agent_list:
                    random_agent = random.choice(agent_list)
                    next_node = MCTSNode(temp_node.task_type, NodeType.AGENT, temp_node, temp_node.depth+1)
                    next_node.data = random_agent
                    agents_used += 1
                elif complete_tool_list and tools_used < tool_quota:
                    # Agent
                    random_tool = random.choice(complete_tool_list)
                    next_node = MCTSNode(temp_node.task_type, NodeType.TOOL, temp_node, temp_node.depth+1)
                    next_node.data = random_tool
                    tools_used += 1
                else:
                    break

            if next_node.depth >= MAX_DEPTH:
                next_node.terminal = True

            response = next_node.action(task, final_content)
            if response is False:
                next_node.terminal = True
                break

            final_content = response
            temp_node = next_node

        #  1: 
        output_code_files = filter_code(final_content)

        #  2: 
        if not output_code_files:
            score = ROLLOUT_PENALTY_CONFIG.get('no_code_penalty', 0.0)
            if ROLLOUT_PENALTY_CONFIG.get('enable_penalty_logging', False):
                logger.warning(f"MCTS Simulation: No code output, applying penalty score of {score}.")
            try:
                logger.info(f"[ITER_SIM] iter={self.current_iter} reward=no_code_penalty files(P1,P2)=0,0 mode=cosine")
            except Exception:
                pass
        else:
            output_code_content = codes_to_content(output_code_files)
            score = evaluate_similarity(output_code_content, ground_truth_code)
            logger.debug(f"MCTS Simulation: Code output detected. Similarity score: {score:.3f}")

        curr_node.expanded = True
        return score


    def backup(self, node: MCTSNode, reward):
        """"""
        while node is not None:
            node.update(reward)
            node = node.parent

    def color_tree(self):
        """"""
        node = self.root
        if not ENABLE_COLORING:
            self._set_all_nodes_black(node)
            return
        score_list = self.calc_node_score(node)
        beta_quantile = self.get_beta_quantile(score_list, BETA)
        self.color_all_nodes(node, beta_quantile)
    
    def _set_all_nodes_black(self, node: MCTSNode):
        """/"""
        node.color = "black"
        for child in node.children:
            self._set_all_nodes_black(child)
    
    def color_all_nodes(self, node: MCTSNode, beta_quantile):
        """"""
        if node.is_leaf_node():
            node.color = "black"
            return
        q = node.value / node.visits if node.visits > 0 else 0
        d = (node.depth + 1) / (MAX_DEPTH + 1)
        w = len(node.children) / MAX_CHILDREN_NUMBER
        score = q * d * w
        if score >= beta_quantile:
            node.color = "red"
            child_status = True
            for child in node.children:
                if not child.is_terminal():
                    child_status = False
                    break
            if child_status:
                node.color = "black"
        else:
            node.color = "black"
        for child in node.children:
            self.color_all_nodes(child, beta_quantile)
        return
    
    def calc_node_score(self, node: MCTSNode, score_list=None):
        """"""
        if score_list is None:
            score_list = []
        value = node.value
        visits = node.visits
        q = value / visits if visits > 0 else 0
        d = (node.depth + 1) / (MAX_DEPTH + 1)
        w = len(node.children) / MAX_CHILDREN_NUMBER
        score = q * d * w
        score_list.append(score)
        for child in node.children:
            self.calc_node_score(child, score_list)
        return score_list
    
    def get_beta_quantile(self, score_list, beta=BETA):
        """"""
        sorted_scores = sorted(score_list, reverse=True)
        index = int(len(sorted_scores) * beta)
        if index >= len(sorted_scores):
            index = len(sorted_scores) - 1
        return sorted_scores[index]

    def best_workflow(self):
        """
        - 
        -  Agent 
        -  Agent 
        - 
        """
        path = []
        node = self.root
        while node and node.children:
            next_node = node.best_child_for_eval()
            if next_node is None or next_node.visits == 0:
                break
            path.append(next_node)
            node = next_node
            if node.is_terminal():
                break
        
        #  Agent  Tool
        start_idx = 0
        while start_idx < len(path) and not path[start_idx].is_agent():
            start_idx += 1
        if start_idx < len(path):
            path = path[start_idx:]
        else:
            path = []
        
        #  Agent  Tool 
        if len(path) < MIN_WORKFLOW_LENGTH:
            candidate_nodes = [c for c in self.root.children if c.visits > 0]
            candidate_nodes.sort(key=lambda c: (c.value / c.visits), reverse=True)
            
            #  value 
            if not candidate_nodes:
                candidate_nodes = list(self.root.children)
                candidate_nodes.sort(key=lambda c: (1 if c.visits > 0 else 0, c.value), reverse=True)
            
            for cand in candidate_nodes:
                if len(path) >= MIN_WORKFLOW_LENGTH:
                    break
                if cand not in path:
                    path.append(cand)
        
        return path
    
    def print_mcts_tree(self):
        """ + """
        node = self.root
        def traverse(node, depth=0):
            data = node.data
            if data is None:
                data = "unknown"
            name = "unknown"
            role = "unknown"
            if data and "Name:" in str(data) and "Role:" in str(data):
                try:
                    name = str(data).split("Name:")[1].split("\n")[0].strip()
                    role = str(data).split("Role:")[1].split("\n")[0].strip()
                except IndexError:
                    pass
            else:
                name = str(data)[:20] if data else "unknown"
            
            color = node.color
            
            enhancement_info = ""
            if (ENHANCEMENT_MODULES_AVAILABLE and hasattr(node, 'current_problems') 
                and ENHANCEMENT_CONFIG['debug_mode']):
                problem_count = len(node.current_problems.problems) if node.current_problems else 0
                potential = node.potential_score.overall_potential if node.potential_score else 0.0
                enhancement_info = f" [P:{problem_count},Pot:{potential:.2f}]"
            
            node_info = f"{'  ' * depth}Name: {name}, Color: {color}{enhancement_info}\n"
            for child in node.children:
                node_info += traverse(child, depth + 1)
            return node_info
        
        tree_str = traverse(node)
        logger.info(f"MCTS Tree:\n{tree_str}")

    def save_tree_to_file(self, file_path):
        """"""
        tree_dict = self.root.to_dict()
        output_dir = os.path.dirname(file_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        if os.path.exists(file_path):
            with open(file_path, 'r+', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_data.append(tree_dict)
                    else:
                        existing_data = [existing_data, tree_dict]
                except json.JSONDecodeError:
                    existing_data = [tree_dict]
                f.seek(0)
                json.dump(existing_data, f, indent=4)
                f.truncate()
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([tree_dict], f, indent=4)
    
    @staticmethod
    def load_tree_from_file(file_path, train_data, tool_list):
        """"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        root_data = data[-1]  # Load the last saved tree
                    else:
                        root_data = data
                    root = MCTSNode.from_dict(root_data)
                    return MCTS(root, train_data, tool_list)
                except json.JSONDecodeError:
                    pass
        # If file does not exist or cannot be loaded, create a new tree
        root = MCTSNode(task_type=TaskType.CODE, type=NodeType.AGENT)
        return MCTS(root, train_data, tool_list)
    
    def get_enhancement_status(self):
        """"""
        if not ENHANCEMENT_MODULES_AVAILABLE:
            return {"status": "disabled", "reason": "Enhancement modules not available"}
        
        return {
            "status": "enabled",
            "statistics": self.enhancement_statistics,
            "config": ENHANCEMENT_CONFIG,
            "components": {
                "potential_calculator": self.potential_calculator is not None
            }
        }
