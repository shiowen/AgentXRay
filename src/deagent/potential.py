"""Agent potential scoring for problem-aware search."""

import logging
from typing import TYPE_CHECKING, Dict, List, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

from deagent.problem_analysis.problem_types import SeverityLevel

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from deagent.problem_analysis.problem_types import ProblemList

@dataclass
class PotentialScore:
    """"""
    overall_potential: float              #  (0-1)
    category_potentials: Dict[str, float] # 
    confidence: float                     #  (0-1)
    reasoning: List[str]                  # 
    capability_evidence: Dict             # 
    similarity_factors: Dict              # 
    
    def __post_init__(self):
        self.overall_potential = max(0.0, min(1.0, self.overall_potential))
        for category in self.category_potentials:
            self.category_potentials[category] = max(0.0, min(1.0, self.category_potentials[category]))

class AgentPotentialCalculator:
    """Agent"""
    
    def __init__(self, similarity_calculator: 'ProblemSimilarityCalculator' = None):
        """
        
        
        Args:
            similarity_calculator: 
        """
        self.similarity_calculator = similarity_calculator
        
        self.potential_weights = {
            'capability_match': 0.35,      # 
            'similarity_match': 0.25,        # 
            'recent_performance': 0.20,      # 
            'expertise_match': 0.15,         # 
            'problem_complexity': 0.05       # 
        }
        
        self.time_decay_factor = 0.95  # 
        self.max_decay_days = 30       # 
        
        self.base_potential = 0.1      # 
        self.max_potential_boost = 0.8 # 
        
        self.similarity_thresholds = {
            'high_similarity': 0.8,       # 
            'medium_similarity': 0.5,     # 
            'low_similarity': 0.2         # 
        }
    
    def calculate_agent_potential(self, agent_profile: str, 
                                target_problems: 'ProblemList',
                                context_info: Dict = None) -> PotentialScore:
        """
        Agent
        
        Args:
            agent_profile: Agentprofile
            target_problems: 
            context_info: 
            
        Returns:
            PotentialScore: 
        """
        if not target_problems or not target_problems.problems:
            return self._create_fallback_potential_score("No target problems provided")
        
        try:
            # 1. Agent
            agent_role = self._extract_agent_role(agent_profile)
            agent_type = self._extract_agent_type(agent_profile)
            
            # 2. Agent
            capability_profiles = self._get_agent_capabilities(agent_role)
            
            # 3. 
            capability_potential = self._calculate_capability_potential(
                capability_profiles, target_problems
            )
            
            similarity_potential = self._calculate_similarity_potential(
                agent_role, target_problems
            )
            
            recent_performance_potential = self._calculate_recent_performance_potential(
                capability_profiles, target_problems
            )
            
            expertise_potential = self._calculate_expertise_potential(
                agent_profile, target_problems
            )
            
            complexity_potential = self._calculate_complexity_adaptation_potential(
                capability_profiles, target_problems
            )
            
            # 4. 
            overall_potential = (
                self.potential_weights['capability_match'] * capability_potential +
                self.potential_weights['similarity_match'] * similarity_potential +
                self.potential_weights['recent_performance'] * recent_performance_potential +
                self.potential_weights['expertise_match'] * expertise_potential +
                self.potential_weights['problem_complexity'] * complexity_potential
            )
            
            # 5. 
            overall_potential = self._apply_time_decay_and_adjustments(
                overall_potential, capability_profiles
            )
            
            # 6. 
            category_potentials = self._calculate_category_potentials(
                capability_profiles, target_problems
            )
            
            # 7. 
            confidence = self._calculate_confidence(
                capability_profiles, target_problems, overall_potential
            )
            
            # 8. 
            reasoning, evidence, similarity_factors = self._generate_reasoning_and_evidence(
                agent_role, target_problems, overall_potential,
                capability_potential, similarity_potential, 
                recent_performance_potential, expertise_potential
            )
            
            return PotentialScore(
                overall_potential=overall_potential,
                category_potentials=category_potentials,
                confidence=confidence,
                reasoning=reasoning,
                capability_evidence=evidence,
                similarity_factors=similarity_factors
            )
            
        except Exception as e:
            return self._create_fallback_potential_score(f"Calculation error: {str(e)}")
    
    def _calculate_capability_potential(self, capability_profiles: Dict, 
                                      target_problems: 'ProblemList') -> float:
        """"""
        if not capability_profiles:
            return self.base_potential
        
        category_scores = []
        for problem in target_problems.problems:
            category = problem.category.value
            if category in capability_profiles:
                profile = capability_profiles[category]
                base_score = profile.success_rate
                confidence_factor = min(profile.total_attempts / 10.0, 1.0)
                improvement_factor = min(profile.average_improvement / 0.3, 1.0)
                
                score = base_score * confidence_factor * (0.7 + 0.3 * improvement_factor)
                category_scores.append(score * problem.priority_score)
            else:
                category_scores.append(self.base_potential * problem.priority_score)
        
        if category_scores:
            total_priority = sum(p.priority_score for p in target_problems.problems)
            return sum(category_scores) / total_priority if total_priority > 0 else self.base_potential
        
        return self.base_potential
    
    def _calculate_similarity_potential(self, agent_role: str, 
                                      target_problems: 'ProblemList') -> float:
        """"""
        if not self.similarity_calculator:
            return 0.5  # 

        return 0.5
    
    def _calculate_recent_performance_potential(self, capability_profiles: Dict,
                                              target_problems: 'ProblemList') -> float:
        """"""
        if not capability_profiles:
            return 0.5
        
        recent_scores = []
        for problem in target_problems.problems:
            category = problem.category.value
            if category in capability_profiles:
                profile = capability_profiles[category]
                if profile.recent_attempts:
                    recent_successes = sum(1 for score in profile.recent_attempts if score > 0.05)
                    recent_success_rate = recent_successes / len(profile.recent_attempts)
                    
                    trend_score = profile.trend_score
                    
                    recent_score = recent_success_rate * 0.6 + trend_score * 0.4
                    recent_scores.append(recent_score * problem.priority_score)
                else:
                    recent_scores.append(0.3 * problem.priority_score)  # 
            else:
                recent_scores.append(0.2 * problem.priority_score)
        
        if recent_scores:
            total_priority = sum(p.priority_score for p in target_problems.problems)
            return sum(recent_scores) / total_priority if total_priority > 0 else 0.3
        
        return 0.3
    
    def _calculate_expertise_potential(self, agent_profile: str,
                                     target_problems: 'ProblemList') -> float:
        """"""
        # Agent profile
        profile_keywords = self._extract_profile_keywords(agent_profile)
        
        problem_keywords = set()
        for problem in target_problems.problems:
            if problem.keywords:
                problem_keywords.update(problem.keywords)
        
        if not profile_keywords or not problem_keywords:
            return 0.4  # 
        
        overlap = len(profile_keywords.intersection(problem_keywords))
        total_keywords = len(profile_keywords.union(problem_keywords))
        
        if total_keywords == 0:
            return 0.4
        
        keyword_similarity = overlap / total_keywords
        
        # Agent
        agent_type = self._extract_agent_type(agent_profile)
        if agent_type == "code":
            # Agent
            technical_keywords = {'function', 'class', 'interface', 'algorithm', 'implementation'}
            technical_overlap = len(profile_keywords.intersection(technical_keywords))
            if technical_overlap > 0:
                keyword_similarity += 0.2  # 
        
        return min(keyword_similarity, 1.0)
    
    def _calculate_complexity_adaptation_potential(self, capability_profiles: Dict,
                                                 target_problems: 'ProblemList') -> float:
        """"""
        if not capability_profiles or not target_problems.problems:
            return 0.5
        
        complexity_scores = []
        for problem in target_problems.problems:
            severity_complexity = {
                SeverityLevel.LOW: 0.2,
                SeverityLevel.MEDIUM: 0.5,
                SeverityLevel.HIGH: 0.8,
                SeverityLevel.CRITICAL: 1.0
            }
            
            problem_complexity = severity_complexity.get(problem.severity, 0.5)
            
            # Agent
            category = problem.category.value
            if category in capability_profiles:
                profile = capability_profiles[category]
                max_improvement = profile.best_improvement
                complexity_adaptation = min(max_improvement / 0.5, 1.0)  # 0.5
                
                # Agent
                if problem_complexity <= 0.5 and complexity_adaptation >= 0.6:
                    score = 0.8  # Agent
                elif problem_complexity > 0.5 and complexity_adaptation >= 0.8:
                    score = 0.9  # Agent
                elif abs(problem_complexity - complexity_adaptation) <= 0.3:
                    score = 0.7  # 
                else:
                    score = 0.4  # 
                
                complexity_scores.append(score * problem.priority_score)
            else:
                complexity_scores.append(0.3 * problem.priority_score)
        
        if complexity_scores:
            total_priority = sum(p.priority_score for p in target_problems.problems)
            return sum(complexity_scores) / total_priority if total_priority > 0 else 0.5
        
        return 0.5
    
    def _apply_time_decay_and_adjustments(self, base_potential: float,
                                        capability_profiles: Dict) -> float:
        """"""
        if not capability_profiles:
            return base_potential
        
        current_time = datetime.now()
        decay_factors = []
        
        for profile in capability_profiles.values():
            if profile.last_success_time:
                try:
                    last_success = datetime.fromisoformat(profile.last_success_time)
                    days_since = (current_time - last_success).days
                    decay_factor = self.time_decay_factor ** min(days_since, self.max_decay_days)
                    decay_factors.append(decay_factor)
                except Exception as exc:
                    logger.debug("Failed to parse last_success_time %r: %s", profile.last_success_time, exc)
                    decay_factors.append(0.8)  # 
            else:
                decay_factors.append(0.5)  # 
        
        if decay_factors:
            average_decay = sum(decay_factors) / len(decay_factors)
            adjusted_potential = base_potential * (0.7 + 0.3 * average_decay)
        else:
            adjusted_potential = base_potential * 0.7
        
        return min(adjusted_potential, 1.0)
    
    def _calculate_category_potentials(self, capability_profiles: Dict,
                                     target_problems: 'ProblemList') -> Dict[str, float]:
        """"""
        category_potentials = {}
        
        for problem in target_problems.problems:
            category = problem.category.value
            if category not in category_potentials:
                if category in capability_profiles:
                    profile = capability_profiles[category]
                    potential = (
                        profile.success_rate * 0.4 +
                        min(profile.average_improvement / 0.3, 1.0) * 0.3 +
                        profile.trend_score * 0.3
                    )
                    category_potentials[category] = min(potential, 1.0)
                else:
                    category_potentials[category] = self.base_potential
        
        return category_potentials
    
    def _calculate_confidence(self, capability_profiles: Dict,
                            target_problems: 'ProblemList',
                            overall_potential: float) -> float:
        """"""
        confidence_factors = []
        
        # 1. 
        total_attempts = sum(profile.total_attempts for profile in capability_profiles.values())
        data_confidence = min(total_attempts / 20.0, 1.0)  # 20
        confidence_factors.append(data_confidence)
        
        # 2. 
        covered_categories = len([p for p in target_problems.problems 
                                if p.category.value in capability_profiles])
        total_categories = len(target_problems.problems)
        coverage_confidence = covered_categories / total_categories if total_categories > 0 else 0.0
        confidence_factors.append(coverage_confidence)
        
        # 3. 
        if capability_profiles:
            category_potentials = [
                cap.success_rate for cap in capability_profiles.values()
                if cap.total_attempts > 0
            ]
            if len(category_potentials) > 1:
                consistency = 1.0 - (max(category_potentials) - min(category_potentials))
                consistency_confidence = max(consistency, 0.0)
            else:
                consistency_confidence = 0.7
            confidence_factors.append(consistency_confidence)
        
        # 4. 
        current_time = datetime.now()
        freshness_scores = []
        for profile in capability_profiles.values():
            if profile.last_success_time:
                try:
                    last_success = datetime.fromisoformat(profile.last_success_time)
                    days_since = (current_time - last_success).days
                    freshness = max(0.0, 1.0 - days_since / 30.0)  # 30
                    freshness_scores.append(freshness)
                except Exception as exc:
                    logger.debug("Failed to parse last_success_time %r: %s", profile.last_success_time, exc)
                    freshness_scores.append(0.3)
        
        if freshness_scores:
            freshness_confidence = sum(freshness_scores) / len(freshness_scores)
            confidence_factors.append(freshness_confidence)
        
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.3  # 
    
    def _generate_reasoning_and_evidence(self, agent_role: str, target_problems: 'ProblemList',
                                       overall_potential: float, capability_potential: float,
                                       similarity_potential: float, recent_performance_potential: float,
                                       expertise_potential: float) -> Tuple[List[str], Dict, Dict]:
        """"""
        reasoning = []
        evidence = {}
        similarity_factors = {}
        
        if overall_potential >= 0.8:
            reasoning.append(f"Agent {agent_role} shows excellent potential for solving these problems")
        elif overall_potential >= 0.6:
            reasoning.append(f"Agent {agent_role} shows good potential for solving these problems")
        elif overall_potential >= 0.4:
            reasoning.append(f"Agent {agent_role} shows moderate potential for solving these problems")
        else:
            reasoning.append(f"Agent {agent_role} shows limited potential for solving these problems")
        
        if capability_potential >= 0.7:
            reasoning.append("Strong capability match in similar problem categories")
        elif capability_potential <= 0.3:
            reasoning.append("Limited capability match in similar problem categories")
        
        if similarity_potential >= 0.7:
            reasoning.append("High similarity to previously solved problems")
        elif similarity_potential <= 0.3:
            reasoning.append("Low similarity to previously solved problems")
        
        if recent_performance_potential >= 0.7:
            reasoning.append("Recent performance shows positive trend")
        elif recent_performance_potential <= 0.3:
            reasoning.append("Recent performance shows declining trend")
        
        if expertise_potential >= 0.7:
            reasoning.append("Strong expertise match with problem requirements")
        elif expertise_potential <= 0.3:
            reasoning.append("Limited expertise match with problem requirements")
        
        evidence = {
            'capability_potential': capability_potential,
            'similarity_potential': similarity_potential,
            'recent_performance_potential': recent_performance_potential,
            'expertise_potential': expertise_potential,
            'agent_role': agent_role,
            'target_problem_count': len(target_problems.problems) if target_problems else 0
        }
        
        similarity_factors = {
            'similarity_threshold_high': self.similarity_thresholds['high_similarity'],
            'similarity_threshold_medium': self.similarity_thresholds['medium_similarity'],
            'similarity_threshold_low': self.similarity_thresholds['low_similarity'],
            'similarity_weight': self.potential_weights['similarity_match']
        }
        
        return reasoning, evidence, similarity_factors
    
    
    def _extract_agent_role(self, agent_profile: str) -> str:
        """Agent profile"""
        # Role
        import re
        role_match = re.search(r'Role[:]\s*([^\n]+)', agent_profile)
        if role_match:
            return role_match.group(1).strip()
        
        # Namefallback
        name_match = re.search(r'Name[:]\s*([^\n]+)', agent_profile)
        if name_match:
            return name_match.group(1).strip()
        
        # profilehash
        import hashlib
        profile_hash = hashlib.md5(agent_profile.encode()).hexdigest()
        return f"agent_{profile_hash[:8]}"
    
    def _extract_agent_type(self, agent_profile: str) -> str:
        """Agent profile"""
        profile_lower = agent_profile.lower()
        if 'work output: code' in profile_lower or 'output: code' in profile_lower:
            return "code"
        elif 'work output: non-code' in profile_lower or 'output: non-code' in profile_lower:
            return "non-code"
        else:
            # profile
            if any(keyword in profile_lower for keyword in ['programmer', 'developer', 'coder', 'engineer']):
                return "code"
            else:
                return "non-code"
    
    def _extract_profile_keywords(self, agent_profile: str) -> Set[str]:
        """Agent profile"""
        import re
        
        text = agent_profile.lower()
        
        keywords = set()
        
        tech_terms = {
            'python', 'java', 'javascript', 'programming', 'coding', 'development',
            'algorithm', 'data', 'structure', 'function', 'class', 'interface',
            'design', 'architecture', 'testing', 'debugging', 'optimization',
            'analysis', 'implementation', 'integration', 'documentation'
        }
        
        for term in tech_terms:
            if term in text:
                keywords.add(term)
        
        action_words = re.findall(r'\b(design|develop|implement|analyze|optimize|test|debug|create|build|manage)\w*\b', text)
        keywords.update(action_words)
        
        return keywords
    
    def _get_agent_capabilities(self, agent_role: str) -> Dict:
        """Agent"""
        return {}
    
    def _create_fallback_potential_score(self, reason: str) -> PotentialScore:
        """"""
        return PotentialScore(
            overall_potential=self.base_potential,
            category_potentials={},
            confidence=0.1,
            reasoning=[f"Fallback potential score: {reason}"],
            capability_evidence={},
            similarity_factors={}
        )
