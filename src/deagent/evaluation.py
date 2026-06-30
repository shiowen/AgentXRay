#!/usr/bin/env python3
"""
Improved Static Functional Equivalence Evaluator - evaluation.py (Final Version)
Optimized weight allocation and semantic recognition for better accuracy.
Added detailed difference analysis functionality and a robust multi-file parser.
"""

import os
import ast
import re
import json
import time
from typing import Dict, List, Any, Optional, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict, Counter
from deagent.utils import logger  # :  training.log

class StaticFunctionalEvaluator:
    """
    Improved Static Functional Equivalence Evaluator
    """
    
    def __init__(self):
        # Weight allocation
        self.functional_weights = {
            'interface_equivalence': 0.20,
            'logic_equivalence': 0.50,
            'semantic_equivalence': 0.30
        }
        
        self.equivalence_thresholds = {
            'perfect_equivalence': 0.90,
            'high_equivalence': 0.70,
            'moderate_equivalence': 0.50,
            'low_equivalence': 0.35
        }
        
        # Semantic synonym dictionary (extended)
        self.semantic_synonyms = {
            'add': ['addition', 'plus', 'sum', 'append', 'extend'],
            'subtract': ['subtraction', 'minus', 'sub'],
            'multiply': ['multiplication', 'times', 'mult'],
            'divide': ['division', 'div'],
            'calculate': ['compute', 'calc', 'process', 'derive'],
            'average': ['mean', 'avg'],
            'format': ['display', 'show', 'render', 'print', 'visualize', 'plot'],
            'get': ['retrieve', 'fetch', 'obtain', 'load'],
            'set': ['assign', 'update', 'modify', 'configure'],
            'create': ['make', 'build', 'generate', 'construct'],
            'delete': ['remove', 'clear', 'destroy', 'drop'],
            'validate': ['check', 'verify', 'test', 'assert'],
            'initialize': ['init', 'setup', 'start', 'bootstrap'],
            'finalize': ['finish', 'complete', 'end', 'close'],
            'save': ['persist', 'dump', 'store', 'write'],
            'load': ['read', 'ingest', 'deserialize'],
            'predict': ['infer', 'forecast'],
            'train': ['fit', 'optimize', 'learn'],
            'evaluate': ['score', 'assess', 'benchmark'],
            'merge': ['join', 'concatenate', 'combine'],
            'filter': ['select', 'where', 'subset'],
            'sort': ['order', 'rank'],
            'update': ['refresh', 'sync'],
        }
        
        # Difference analysis categories
        self.difference_categories = {
            'interface_mismatch': "Interface structure mismatch",
            'logic_difference': "Logic implementation difference",
            'semantic_difference': "Semantic intent difference",
            'functionality_missing': "Missing or extra functionality",
            'architecture_difference': "Architecture organization difference"
        }
    
    def evaluate_multifile_similarity(self, project1: Dict[str, str], project2: Dict[str, str], 
                                    return_analysis: bool = False) -> float:
        """
        Multi-file project static functional equivalence evaluation main interface
        """
        try:
            analysis_result = self._static_functional_analysis(project1, project2)
            
            if return_analysis:
                return analysis_result
            else:
                return analysis_result['overall_similarity']
                
        except Exception as e:
            logger.warning("Static functional equivalence evaluation failed: %s", e)
            return 0.0
    
    def _static_functional_analysis(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        """Static functional equivalence analysis"""
        analysis = {
            'overall_similarity': 0.0,
            'equivalence_detected': False,
            'equivalence_type': [],
            'equivalence_confidence': 0.0,
            'difference_summary': "",
            'detailed_differences': {},
            'critical_issues': [],
            'recommendations': [],
            'dimension_scores': {},
            'execution_time': 0.0,
            'equivalence_details': {}
        }
        
        start_time = time.time()
        
        try:
            interface_result = self._analyze_interface_equivalence_improved(project1, project2)
            analysis['dimension_scores']['interface_equivalence'] = interface_result['score']
            analysis['equivalence_details']['interface'] = interface_result
            
            logic_result = self._analyze_logic_equivalence_improved(project1, project2)
            analysis['dimension_scores']['logic_equivalence'] = logic_result['score']
            analysis['equivalence_details']['logic'] = logic_result
            
            semantic_result = self._analyze_semantic_equivalence_improved(project1, project2)
            analysis['dimension_scores']['semantic_equivalence'] = semantic_result['score']
            analysis['equivalence_details']['semantic'] = semantic_result
            
            analysis['overall_similarity'] = (
                self.functional_weights['interface_equivalence'] * interface_result['score'] +
                self.functional_weights['logic_equivalence'] * logic_result['score'] +
                self.functional_weights['semantic_equivalence'] * semantic_result['score']
            )
            
            analysis['equivalence_detected'] = analysis['overall_similarity'] >= self.equivalence_thresholds['low_equivalence']
            analysis['equivalence_confidence'] = analysis['overall_similarity']
            analysis['equivalence_type'] = self._determine_equivalence_types(interface_result, logic_result, semantic_result)
            analysis.update(self._generate_static_difference_analysis(analysis['overall_similarity']))
            analysis['detailed_differences'] = self._compile_detailed_differences(analysis['equivalence_details'])

        except Exception as e:
            analysis['critical_issues'].append(f"Static analysis process error: {str(e)}")
        
        analysis['execution_time'] = time.time() - start_time
        return analysis
    
    def _analyze_interface_equivalence_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'score': 0.0, 'function_signatures': {'similarity': 0.0, 'details': {}}, 'class_structures': {'similarity': 0.0, 'details': {}}, 'module_organization': {'similarity': 0.0, 'details': {}}, 'differences': [], 'reasons': []}
        try:
            func_analysis = self._analyze_function_signatures_improved(project1, project2)
            result['function_signatures'] = func_analysis
            class_analysis = self._analyze_class_structures_improved(project1, project2)
            result['class_structures'] = class_analysis
            module_analysis = self._analyze_module_organization_improved(project1, project2)
            result['module_organization'] = module_analysis
            result['score'] = (func_analysis['similarity'] * 0.50 + class_analysis['similarity'] * 0.30 + module_analysis['similarity'] * 0.20)
            if func_analysis['similarity'] > 0.6: result['reasons'].append("Function interfaces similar")
            elif func_analysis['similarity'] < 0.3: result['differences'].append("Function interface differences significant")
            if class_analysis['similarity'] > 0.6: result['reasons'].append("Class structures similar")
            elif class_analysis['similarity'] < 0.3: result['differences'].append("Class structure differences significant")
        except Exception as e: result['differences'].append(f"Interface equivalence analysis error: {str(e)}")
        return result
    
    def _analyze_logic_equivalence_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'score': 0.0, 'algorithm_patterns': {'similarity': 0.0, 'details': {}}, 'control_flow': {'similarity': 0.0, 'details': {}}, 'computational_logic': {'similarity': 0.0, 'details': {}}, 'differences': [], 'reasons': []}
        try:
            algorithm_analysis = self._analyze_algorithm_patterns_improved(project1, project2)
            result['algorithm_patterns'] = algorithm_analysis
            control_analysis = self._analyze_control_flow_improved(project1, project2)
            result['control_flow'] = control_analysis
            computation_analysis = self._analyze_computational_logic_improved(project1, project2)
            result['computational_logic'] = computation_analysis
            result['score'] = (algorithm_analysis['similarity'] * 0.40 + control_analysis['similarity'] * 0.30 + computation_analysis['similarity'] * 0.30)
            if algorithm_analysis['similarity'] > 0.6: result['reasons'].append("Algorithm patterns similar")
            elif algorithm_analysis['similarity'] < 0.3: result['differences'].append("Algorithm implementation methods differ")
            if control_analysis['similarity'] > 0.6: result['reasons'].append("Control flow structures similar")
            elif control_analysis['similarity'] < 0.3: result['differences'].append("Control flow logic differences significant")
        except Exception as e: result['differences'].append(f"Logic equivalence analysis error: {str(e)}")
        return result
    
    def _analyze_semantic_equivalence_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'score': 0.0, 'naming_semantics': {'similarity': 0.0, 'details': {}}, 'code_intent': {'similarity': 0.0, 'details': {}}, 'differences': [], 'reasons': []}
        try:
            naming_analysis = self._analyze_naming_semantics_improved(project1, project2)
            result['naming_semantics'] = naming_analysis
            intent_analysis = self._analyze_code_intent_improved(project1, project2)
            result['code_intent'] = intent_analysis
            result['score'] = (naming_analysis['similarity'] * 0.60 + intent_analysis['similarity'] * 0.40)
            if naming_analysis['similarity'] > 0.5: result['reasons'].append("Naming semantics similar")
            elif naming_analysis['similarity'] < 0.3: result['differences'].append("Naming style and semantics differ")
            if intent_analysis['similarity'] > 0.5: result['reasons'].append("Code intent similar")
            elif intent_analysis['similarity'] < 0.3: result['differences'].append("Code intent differs")
        except Exception as e: result['differences'].append(f"Semantic equivalence analysis error: {str(e)}")
        return result
    
    def _analyze_function_signatures_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            signatures1 = self._extract_function_signatures(project1)
            signatures2 = self._extract_function_signatures(project2)
            names1 = [sig['name'] for sig in signatures1]; names2 = [sig['name'] for sig in signatures2]
            semantic_similarity = self._calculate_semantic_name_similarity(names1, names2)
            patterns1 = Counter(f"{sig['name']}({sig['param_count']})" for sig in signatures1)
            patterns2 = Counter(f"{sig['name']}({sig['param_count']})" for sig in signatures2)
            param_similarity = self._calculate_counter_similarity_improved(patterns1, patterns2)
            count_similarity = self._calculate_count_similarity(len(signatures1), len(signatures2))
            result['similarity'] = (semantic_similarity * 0.50 + param_similarity * 0.30 + count_similarity * 0.20)
            result['details'] = {'p1_signatures': [f"{sig['name']}({sig['param_count']})" for sig in signatures1], 'p2_signatures': [f"{sig['name']}({sig['param_count']})" for sig in signatures2], 'semantic_similarity': semantic_similarity, 'param_similarity': param_similarity, 'count_similarity': count_similarity}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _analyze_class_structures_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            classes1 = self._extract_class_structures(project1)
            classes2 = self._extract_class_structures(project2)
            if not classes1 and not classes2: result['similarity'] = 1.0; return result
            if not classes1 or not classes2: result['similarity'] = 0.5; return result
            names1 = [cls['name'] for cls in classes1]; names2 = [cls['name'] for cls in classes2]
            class_semantic_similarity = self._calculate_semantic_name_similarity(names1, names2)
            method_patterns1 = [f"{cls['name']}.{method['name']}" for cls in classes1 for method in cls['methods']]
            method_patterns2 = [f"{cls['name']}.{method['name']}" for cls in classes2 for method in cls['methods']]
            method_similarity = self._calculate_semantic_name_similarity(method_patterns1, method_patterns2)
            count_similarity = self._calculate_count_similarity(len(classes1), len(classes2))
            result['similarity'] = (class_semantic_similarity * 0.40 + method_similarity * 0.40 + count_similarity * 0.20)
            result['details'] = {'p1_classes': names1, 'p2_classes': names2, 'p1_methods': method_patterns1, 'p2_methods': method_patterns2, 'class_semantic_similarity': class_semantic_similarity, 'method_similarity': method_similarity, 'count_similarity': count_similarity}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _analyze_module_organization_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            basenames1 = set(os.path.splitext(f)[0].lower() for f in project1.keys())
            basenames2 = set(os.path.splitext(f)[0].lower() for f in project2.keys())
            filename_similarity = self._calculate_semantic_name_similarity(list(basenames1), list(basenames2))
            imports1 = self._extract_import_relationships(project1)
            imports2 = self._extract_import_relationships(project2)
            import_similarity = self._calculate_set_similarity(imports1, imports2)
            result['similarity'] = (filename_similarity * 0.70 + import_similarity * 0.30)
            result['details'] = {'p1_modules': list(basenames1), 'p2_modules': list(basenames2), 'p1_imports': list(imports1), 'p2_imports': list(imports2), 'filename_similarity': filename_similarity, 'import_similarity': import_similarity}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _analyze_algorithm_patterns_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            patterns1 = self._extract_algorithm_patterns_comprehensive(project1)
            patterns2 = self._extract_algorithm_patterns_comprehensive(project2)
            similarity = self._calculate_set_similarity_improved(patterns1, patterns2)
            result['similarity'] = similarity
            result['details'] = {'p1_patterns': list(patterns1), 'p2_patterns': list(patterns2), 'common_patterns': list(patterns1.intersection(patterns2))}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _analyze_control_flow_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            flow1 = self._extract_control_flow_comprehensive(project1)
            flow2 = self._extract_control_flow_comprehensive(project2)
            similarity = self._calculate_counter_similarity_improved(flow1, flow2)
            result['similarity'] = similarity
            result['details'] = {'p1_flow': dict(flow1), 'p2_flow': dict(flow2)}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _analyze_computational_logic_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            computations1 = self._extract_computational_expressions(project1)
            computations2 = self._extract_computational_expressions(project2)
            similarity = self._calculate_set_similarity_improved(computations1, computations2)
            result['similarity'] = similarity
            result['details'] = {'p1_computations': list(computations1), 'p2_computations': list(computations2)}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _analyze_naming_semantics_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            identifiers1 = self._extract_identifiers(project1)
            identifiers2 = self._extract_identifiers(project2)
            semantic_similarity = self._calculate_semantic_name_similarity(list(identifiers1), list(identifiers2))
            result['similarity'] = semantic_similarity
            result['details'] = {'p1_identifiers_count': len(identifiers1), 'p2_identifiers_count': len(identifiers2), 'semantic_similarity': semantic_similarity}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _analyze_code_intent_improved(self, project1: Dict[str, str], project2: Dict[str, str]) -> Dict[str, Any]:
        result = {'similarity': 0.0, 'details': {}}
        try:
            intent1 = self._extract_code_intent_features(project1)
            intent2 = self._extract_code_intent_features(project2)
            similarity = self._calculate_set_similarity_improved(intent1, intent2)
            result['similarity'] = similarity
            result['details'] = {'p1_intent_features': list(intent1), 'p2_intent_features': list(intent2)}
        except Exception as e: result['details']['error'] = str(e)
        return result
    
    def _calculate_semantic_name_similarity(self, names1: List[str], names2: List[str]) -> float:
        if not names1 and not names2: return 1.0
        if not names1 or not names2: return 0.0
        semantic_names1 = {self._normalize_name_semantics(name) for name in names1}
        semantic_names2 = {self._normalize_name_semantics(name) for name in names2}
        intersection = len(semantic_names1.intersection(semantic_names2))
        union = len(semantic_names1.union(semantic_names2))
        return intersection / union if union > 0 else 0.0
    
    def _normalize_name_semantics(self, name: str) -> str:
        name_lower = name.lower()
        for base_word, synonyms in self.semantic_synonyms.items():
            if name_lower == base_word or name_lower in synonyms: return base_word
            for synonym in synonyms:
                if synonym in name_lower: return base_word
        return re.sub(r'(ing|ed|er|ly|tion|ness)$', '', name_lower)
    
    def _calculate_set_similarity_improved(self, set1: Set, set2: Set) -> float:
        if not set1 and not set2: return 1.0
        if not set1 or not set2: return 0.3
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        bonus = 0.2 if union <= 3 else (0.1 if union <= 5 else 0.0)
        base_similarity = intersection / union if union > 0 else 0.0
        return min(base_similarity + bonus, 1.0)
    
    def _calculate_counter_similarity_improved(self, counter1: Counter, counter2: Counter) -> float:
        if not counter1 and not counter2: return 1.0
        if not counter1 or not counter2: return 0.3
        all_keys = set(counter1.keys()).union(set(counter2.keys()))
        if not all_keys: return 1.0
        similarities = []
        for key in all_keys:
            count1, count2 = counter1.get(key, 0), counter2.get(key, 0)
            if count1 == 0 and count2 == 0: similarities.append(1.0)
            elif count1 == 0 or count2 == 0: similarities.append(0.2)
            else:
                max_count = max(count1, count2)
                sim = 1.0 - abs(count1 - count2) / max_count
                similarities.append(sim)
        return sum(similarities) / len(similarities)
    
    def _calculate_count_similarity(self, count1: int, count2: int) -> float:
        if count1 == 0 and count2 == 0: return 1.0
        if count1 == 0 or count2 == 0: return 0.4
        max_count = max(count1, count2)
        return 1.0 - abs(count1 - count2) / max_count
    
    def _extract_function_signatures(self, project: Dict[str, str]) -> List[Dict]:
        signatures = []
        for filename, content in project.items():
            if not filename.endswith('.py'): continue
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef): signatures.append({'name': node.name, 'param_count': len(node.args.args), 'complexity': self._calculate_function_complexity(node), 'file': filename})
            except SyntaxError: continue
        return signatures

    def _extract_class_structures(self, project: Dict[str, str]) -> List[Dict]:
        classes = []
        for filename, content in project.items():
            if not filename.endswith('.py'): continue
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [{'name': item.name, 'param_count': len(item.args.args)} for item in node.body if isinstance(item, ast.FunctionDef)]
                        classes.append({'name': node.name, 'methods': methods, 'file': filename})
            except SyntaxError: continue
        return classes

    def _extract_import_relationships(self, project: Dict[str, str]) -> Set[str]:
        imports = set()
        for filename, content in project.items():
            if not filename.endswith('.py'): continue
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names: imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module)
            except SyntaxError: continue
        return imports

    def _extract_algorithm_patterns_comprehensive(self, project: Dict[str, str]) -> Set[str]:
        patterns = set()
        for content in project.values():
            content_lower = content.lower()
            if any(op in content_lower for op in ['sum(', '+', 'add', 'append(']): patterns.add('summation')
            if any(op in content_lower for op in ['max(', 'min(']): patterns.add('extrema_finding')
            if any(op in content_lower for op in ['/', 'divide', 'average', 'mean']): patterns.add('averaging')
            if any(op in content_lower for op in ['*', 'multiply', 'product']): patterns.add('multiplication')
            if any(op in content_lower for op in ['sort', 'sorted']): patterns.add('sorting')
            if any(op in content_lower for op in ['search', 'find', 'index']): patterns.add('searching')
            if any(op in content_lower for op in ['filter', 'select', 'where']): patterns.add('filtering')
            if 'for ' in content_lower and ' in ' in content_lower: patterns.add('iteration')
            if 'while ' in content_lower: patterns.add('conditional_loop')
            if 'class ' in content_lower and 'def __init__' in content_lower: patterns.add('object_oriented')
            if any(k in content_lower for k in ['dict(', '{', 'json.loads', 'json.dump']): patterns.add('dictionary_usage')
            if any(k in content_lower for k in ['list(', '[', '[]']): patterns.add('list_usage')
            if any(k in content_lower for k in ['set(', 'setdefault']): patterns.add('set_usage')
            # I/O & 
            if any(k in content_lower for k in ['open(', 'read(', 'write(', 'with open']): patterns.add('file_io')
            if any(k in content_lower for k in ['pickle.', 'joblib.', 'json.', 'yaml.']): patterns.add('serialization')
            if any(k in content_lower for k in ['async def', 'await ', 'threading', 'multiprocessing', 'concurrent.futures']): patterns.add('concurrency')
            if any(k in content_lower for k in ['requests.', 'http', 'urllib', 'aiohttp']): patterns.add('network_io')
            # ML / 
            if any(k in content_lower for k in ['sklearn.', 'torch.', 'tensorflow', 'fit(', 'predict(']): patterns.add('ml_pipeline')
            if any(k in content_lower for k in ['pandas.', 'pd.', 'dataframe', 'merge(', 'groupby(']): patterns.add('data_processing')
            if any(k in content_lower for k in ['matplotlib', 'plt.', 'seaborn.', 'plot(', 'figure(']): patterns.add('visualization')
            try:
                tree = ast.parse(content)
                func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
                for n in ast.walk(tree):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in func_names:
                        patterns.add('recursion')
                        break
            except Exception:
                pass
        return patterns

    def _extract_control_flow_comprehensive(self, project: Dict[str, str]) -> Counter:
        flow_patterns = Counter()
        for content in project.values():
            if not content.strip(): continue
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.For): flow_patterns['for_loop'] += 1
                    elif isinstance(node, ast.While): flow_patterns['while_loop'] += 1
                    elif isinstance(node, ast.If): flow_patterns['if_condition'] += 1
                    elif isinstance(node, ast.Try): flow_patterns['try_except'] += 1
                    elif isinstance(node, ast.With): flow_patterns['with_context'] += 1
            except SyntaxError: continue
        return flow_patterns

    def _extract_computational_expressions(self, project: Dict[str, str]) -> Set[str]:
        expressions = set()
        for content in project.values():
            if not content.strip(): continue
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.BinOp):
                        if isinstance(node.op, ast.Add): expressions.add('addition_expr')
                        elif isinstance(node.op, ast.Sub): expressions.add('subtraction_expr')
                        elif isinstance(node.op, ast.Mult): expressions.add('multiplication_expr')
                        elif isinstance(node.op, ast.Div): expressions.add('division_expr')
                    elif isinstance(node, ast.Compare): expressions.add('comparison_expr')
            except SyntaxError: continue
        return expressions

    def _extract_identifiers(self, project: Dict[str, str]) -> Set[str]:
        identifiers = set()
        for content in project.values():
            if not content.strip(): continue
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Name, ast.FunctionDef, ast.ClassDef)):
                        identifiers.add(node.name if hasattr(node, 'name') else node.id)
            except SyntaxError: continue
        return identifiers

    def _extract_code_intent_features(self, project: Dict[str, str]) -> Set[str]:
        intent_features = set()
        for content in project.values():
            content_lower = content.lower()
            if any(w in content_lower for w in ['calculate', 'compute', 'derive']): intent_features.add('computation')
            if any(w in content_lower for w in ['format', 'display', 'show', 'print', 'render', 'plot']): intent_features.add('presentation')
            if any(w in content_lower for w in ['add', 'sum', 'total', 'append', 'extend']): intent_features.add('aggregation')
            if any(w in content_lower for w in ['average', 'mean', 'median']): intent_features.add('averaging')
            if any(w in content_lower for w in ['load', 'read', 'ingest', 'deserialize']): intent_features.add('data_loading')
            if any(w in content_lower for w in ['save', 'write', 'dump', 'persist', 'export']): intent_features.add('data_saving')
            if any(w in content_lower for w in ['fit', 'train', 'optimize', 'learn']): intent_features.add('model_training')
            if any(w in content_lower for w in ['predict', 'infer', 'forecast']): intent_features.add('inference')
            if any(w in content_lower for w in ['evaluate', 'score', 'benchmark', 'validate']): intent_features.add('evaluation')
            if any(w in content_lower for w in ['visualize', 'plot', 'chart', 'graph', 'figure']): intent_features.add('visualization')
            if any(w in content_lower for w in ['config', 'yaml', 'ini', 'settings']): intent_features.add('configuration')
            if any(w in content_lower for w in ['http', 'request', 'response', 'api']): intent_features.add('networking')
            if any(w in content_lower for w in ['async', 'await', 'thread', 'process', 'queue']): intent_features.add('concurrency')
        return intent_features
    
    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        complexity = 1
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)): complexity += 1
            elif isinstance(node, ast.BoolOp): complexity += len(node.values) - 1
            elif isinstance(node, ast.Try): complexity += len(node.handlers)
        return complexity
    
    def _calculate_set_similarity(self, set1: Set, set2: Set) -> float:
        if not set1 and not set2: return 1.0
        if not set1 or not set2: return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0
    
    def _compile_detailed_differences(self, equivalence_details: Dict) -> Dict:
        diffs = {}
        def get_set_diffs(key1, key2, details_dict):
            set1 = set(details_dict.get(key1, [])); set2 = set(details_dict.get(key2, []))
            if set1 or set2:
                p1_only = list(set1 - set2); p2_only = list(set2 - set1)
                if p1_only or p2_only: return {"Project1_unique": sorted(p1_only), "Project2_unique": sorted(p2_only)}
            return None
        interface_diffs = {}; if_details = equivalence_details.get('interface', {})
        sig_diff = get_set_diffs('p1_signatures', 'p2_signatures', if_details.get('function_signatures', {}).get('details', {}))
        if sig_diff: interface_diffs["Function_signature_differences"] = sig_diff
        cls_diff = get_set_diffs('p1_classes', 'p2_classes', if_details.get('class_structures', {}).get('details', {}))
        if cls_diff: interface_diffs["Class_structure_differences"] = cls_diff
        mod_diff = get_set_diffs('p1_modules', 'p2_modules', if_details.get('module_organization', {}).get('details', {}))
        if mod_diff: interface_diffs["Module_organization_differences"] = mod_diff
        if interface_diffs: diffs["Interface_differences"] = interface_diffs
        logic_diffs = {}; logic_details = equivalence_details.get('logic', {})
        algo_diff = get_set_diffs('p1_patterns', 'p2_patterns', logic_details.get('algorithm_patterns', {}).get('details', {}))
        if algo_diff: logic_diffs["Algorithm_pattern_differences"] = algo_diff
        flow_details = logic_details.get('control_flow', {}).get('details', {})
        flow1, flow2 = flow_details.get('p1_flow', {}), flow_details.get('p2_flow', {})
        if flow1 != flow2: logic_diffs["Control_flow_quantity_comparison"] = {"Project1": flow1, "Project2": flow2}
        comp_diff = get_set_diffs('p1_computations', 'p2_computations', logic_details.get('computational_logic', {}).get('details', {}))
        if comp_diff: logic_diffs["Computational_logic_differences"] = comp_diff
        if logic_diffs: diffs["Logic_differences"] = logic_diffs
        semantic_diffs = {}; semantic_details = equivalence_details.get('semantic', {})
        intent_diff = get_set_diffs('p1_intent_features', 'p2_intent_features', semantic_details.get('code_intent', {}).get('details', {}))
        if intent_diff: semantic_diffs["Code_intent_differences"] = intent_diff
        if semantic_diffs: diffs["Semantic_differences"] = semantic_diffs
        return diffs
    
    def _generate_static_difference_analysis(self, overall_score: float) -> Dict[str, Any]:
        analysis = {'difference_summary': "", 'critical_issues': [], 'recommendations': []}
        try:
            if overall_score >= self.equivalence_thresholds['perfect_equivalence']: analysis['difference_summary'] = f"Perfect functional equivalence (Score: {overall_score:.3f}) - Static analysis shows functions are almost identical"
            elif overall_score >= self.equivalence_thresholds['high_equivalence']: analysis['difference_summary'] = f"High functional equivalence (Score: {overall_score:.3f}) - Static analysis shows functions are similar"
            elif overall_score >= self.equivalence_thresholds['moderate_equivalence']: analysis['difference_summary'] = f"Moderate functional equivalence (Score: {overall_score:.3f}) - Some differences exist but functions are basically consistent"
            elif overall_score >= self.equivalence_thresholds['low_equivalence']: analysis['difference_summary'] = f"Low functional equivalence (Score: {overall_score:.3f}) - Some similarity exists but differences are significant"
            else: analysis['difference_summary'] = f"Functions not equivalent (Score: {overall_score:.3f}) - Implementation differences are very significant"
            if overall_score >= 0.70: analysis['recommendations'].append("[Strategy] High functional equivalence, Agent organization is good")
            elif overall_score >= 0.50: analysis['recommendations'].append("[Strategy] Basic functional equivalence, can perform local optimization")
            elif overall_score >= 0.35: analysis['recommendations'].append("[Strategy] Partial functional equivalence, need to adjust Agent strategy")
            else: analysis['recommendations'].append("[Strategy] Functions not equivalent, need to redesign Agent organization")
        except Exception as e: analysis['critical_issues'].append(f"Difference analysis generation error: {str(e)}")
        return analysis
    
    def _determine_equivalence_types(self, interface_result: Dict, logic_result: Dict, semantic_result: Dict) -> List[str]:
        types = []
        if interface_result['score'] > 0.6: types.append("interface_equivalent")
        if logic_result['score'] > 0.55: types.append("logic_equivalent")
        if semantic_result['score'] > 0.50: types.append("semantic_equivalent")
        return types

FunctionalEquivalenceEvaluator = StaticFunctionalEvaluator

def parse_code_content_to_files(content: str) -> Dict[str, str]:
    codebooks = {}
    if not content: 
        return codebooks

    # Tolerate model "preamble" text before the first file header.
    # Many LLM outputs add extra prose; we discard everything before the first
    # file header line to keep the multi-file parser strict.
    lines_for_trim = content.splitlines()
    header_line_re = re.compile(
        r"^(?:File:\s*)?[A-Za-z0-9_./\-]+\.[A-Za-z0-9_]+\s*$",
        re.IGNORECASE,
    )
    first_header_idx: Optional[int] = None
    for i, ln in enumerate(lines_for_trim):
        if header_line_re.match(ln.strip()):
            first_header_idx = i
            break
    if first_header_idx is not None and first_header_idx > 0:
        content = "\n".join(lines_for_trim[first_header_idx:])
    
    # If the model output includes markdown/code fences but no explicit filename headers,
    # treat it as a single-file project instead of failing the parse.
    def _single_file_fallback(raw: str) -> Dict[str, str]:
        # Strip common wrappers while preserving code.
        cleaned = re.sub(r"^```[A-Za-z0-9_+-]*\s*\n", "", raw.strip())
        cleaned = re.sub(r"\n```\s*$", "", cleaned)
        if not cleaned.strip():
            return {}
        return {"main.py": cleaned.strip()}

    # Primary: parse markdown fences with a header line before the block
    regex = r"(.+?)\n```.*?\n(.*?)```"
    matches = list(re.finditer(regex, content, re.DOTALL))
    if matches:
        for match in matches:
            code, group1 = match.group(2), match.group(1)
            if "CODE" in code:
                continue
            filename = ""
            for candidate in re.finditer(r"([A-Za-z0-9_./\-]+\.[A-Za-z0-9_]+)", group1, re.DOTALL):
                filename = candidate.group(1).lower()
                break
            if "__main__" in code and not filename:
                filename = "main.py"
            if filename and code.strip():
                codebooks[filename] = "\n".join(line for line in code.split("\n") if line.strip())
        if codebooks:
            return codebooks
        # Found code fences but no filename headers -> single-file fallback.
        concatenated = "\n\n".join(m.group(2) for m in matches if m.group(2) and m.group(2).strip())
        sf = _single_file_fallback(concatenated)
        if sf:
            return sf

    # Fallback: parse plain "filename line + raw code" sections (no fences)
    lines = content.splitlines()
    current_file = None
    buffer: List[str] = []

    def flush():
        if current_file and buffer:
            code = "\n".join(l for l in buffer if l.strip())
            if code:
                codebooks[current_file] = code

    filename_pattern = re.compile(r"^(?:File:\s*)?([A-Za-z0-9_./\-]+\.[A-Za-z0-9_]+)\s*$", re.IGNORECASE)
    for line in lines:
        m = filename_pattern.match(line.strip())
        if m:
            # new file header encountered
            flush()
            current_file = m.group(1).lower()
            buffer = []
            continue
        # accumulate raw code
        buffer.append(line)
    flush()

    # No file headers detected; if the content looks like raw code, treat as a single file.
    if not codebooks:
        sf = _single_file_fallback(content)
        if sf:
            return sf

    return codebooks

def evaluate_similarity(content1, content2, method='static_functional'):
    if method == 'traditional':
        logger.info('[SIM_EVAL] Forced traditional method (TF-IDF cosine).')
        return calculate_similarity(content1, content2)
    try:
        project1 = parse_code_content_to_files(content1)
        project2 = parse_code_content_to_files(content2)
        if not project1 or not project2:
            logger.warning('[SIM_EVAL] Parsing failed (one or both empty). Falling back to cosine similarity.')
            return calculate_similarity(content1, content2)
        logger.info(f"[SIM_EVAL] Static functional evaluation engaged. Parsed files -> P1:{len(project1)} P2:{len(project2)}")
        evaluator = StaticFunctionalEvaluator()
        score = evaluator.evaluate_multifile_similarity(project1, project2)
        logger.info(f"[SIM_EVAL] Static functional similarity score: {score:.4f}")
        return score
    except Exception as e:
        logger.error(f"[SIM_EVAL] Static evaluation exception: {e}. Falling back to cosine similarity.")
        return calculate_similarity(content1, content2)


def evaluate_similarity_with_analysis(content1, content2):
    try:
        project1 = parse_code_content_to_files(content1)
        project2 = parse_code_content_to_files(content2)
        if not project1 or not project2:
            logger.warning('[SIM_EVAL_ANALYSIS] Parsing failed, using traditional method.')
            fallback = calculate_similarity(content1, content2)
            logger.info(f"[SIM_EVAL_ANALYSIS] Fallback cosine similarity: {fallback:.4f}")
            return fallback, 'Parsing failed, using traditional method'
        logger.info(f"[SIM_EVAL_ANALYSIS] Static functional analysis engaged. Files -> P1:{len(project1)} P2:{len(project2)}")
        evaluator = StaticFunctionalEvaluator()
        analysis = evaluator.evaluate_multifile_similarity(project1, project2, return_analysis=True)
        logger.info(f"[SIM_EVAL_ANALYSIS] Dimension scores: {analysis['dimension_scores']}")
        logger.info(f"[SIM_EVAL_ANALYSIS] Overall similarity: {analysis['overall_similarity']:.4f}")
        diff_text = json.dumps(analysis['detailed_differences'], indent=2, ensure_ascii=False)
        summary_text = analysis['difference_summary']
        if diff_text and diff_text != '{}':
            summary_text += "\n\nDetailed differences:\n" + diff_text
        if analysis['critical_issues']:
            summary_text += "\n\nCritical issues:\n" + "\n".join(analysis['critical_issues'])
        if analysis['recommendations']:
            summary_text += "\n\nImprovement recommendations:\n" + "\n".join(analysis['recommendations'])
        return analysis['overall_similarity'], summary_text
    except Exception as e:
        logger.error(f"[SIM_EVAL_ANALYSIS] Static evaluation error: {e}")
        return 0.0, f"Static evaluation error: {str(e)}"

def calculate_similarity(content1, content2):
    if not content1 and not content2: 
        return 1.0
    if not content1 or not content2: 
        return 0.0
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([content1, content2])
        return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except Exception as exc:
        logger.debug("TF-IDF similarity calculation failed: %s", exc)
        return 0.0

def read_files_from_directory(directory):
    file_contents = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_contents.append(f.read())
            except Exception as exc:
                logger.debug("Failed to read file %s: %s", file_path, exc)
                continue
    return file_contents

def evaluate_similarity_path(project1_path, project2_path, method='static_functional'):
    project1_dict, project2_dict = {}, {}
    try:
        for root, _, files in os.walk(project1_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        project1_dict[os.path.relpath(file_path, project1_path)] = f.read()
        for root, _, files in os.walk(project2_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        project2_dict[os.path.relpath(file_path, project2_path)] = f.read()
        
        if not project1_dict or not project2_dict:
            raise ValueError("One or both projects are empty")

        evaluator = StaticFunctionalEvaluator()
        similarity = evaluator.evaluate_multifile_similarity(project1_dict, project2_dict)
        
    except Exception as e:
        logger.warning("Static evaluation failed; falling back to traditional method: %s", e)
        p1_content = " ".join(read_files_from_directory(project1_path))
        p2_content = " ".join(read_files_from_directory(project2_path))
        return calculate_similarity(p1_content, p2_content)
    
    logger.info("Overall similarity: %.2f", similarity)
    return similarity
