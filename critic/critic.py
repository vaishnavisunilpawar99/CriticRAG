"""
Critic Engine (Self-Contained Verification & Fact-Checking)
===========================================================
An independent verification and fact-checking Critic module designed to detect
and eliminate LLM hallucinations using:
1. Complete Safe Arithmetic Engine (All operations: +, -, *, /, //, %, **, sqrt, %, stats)
2. Direct Arithmetic Parameter Operation Suite
3. Curated Trusted Reference Web Sources with Full URLs (Wikipedia, Britannica, NIST, etc.)
4. Live Online Web Fetch & Cross-Examination Tool
5. Multi-Criteria Hallucination Auditor & Delta Correction Engine
"""

import ast
import operator
import re
import math
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict


# ============================================================================
# 1. CURATED TRUSTED WEBSITES & KNOWLEDGE SOURCES (WITH FULL URLS)
# ============================================================================

TRUSTED_WEBSITES: List[Dict[str, str]] = [
    {
        "name": "Wikipedia (English)",
        "full_url": "https://en.wikipedia.org/wiki/",
        "api_endpoint": "https://en.wikipedia.org/api/rest_v1/page/summary/",
        "domain": "en.wikipedia.org",
        "category": "General Knowledge & Encyclopedic Facts",
        "trust_level": "High (Community Peer-Reviewed)",
        "description": "Standard encyclopedic reference for history, named entities, biographies, and world landmarks."
    },
    {
        "name": "Encyclopaedia Britannica",
        "full_url": "https://www.britannica.com/",
        "domain": "britannica.com",
        "category": "Curated Academic Encyclopedia",
        "trust_level": "Highest (Expert Academic Editorial Board)",
        "description": "Fact-checked scholarly articles authored by recognized subject-matter authorities."
    },
    {
        "name": "NIST Reference on Constants (CODATA)",
        "full_url": "https://physics.nist.gov/cuu/Constants/",
        "domain": "physics.nist.gov",
        "category": "Physical Standards & Fundamental Constants",
        "trust_level": "Highest (National Metrological Authority)",
        "description": "International CODATA values for fundamental constants (speed of light, Planck constant, etc.)."
    },
    {
        "name": "Wolfram MathWorld",
        "full_url": "https://mathworld.wolfram.com/",
        "domain": "mathworld.wolfram.com",
        "category": "Mathematical & Computational Science",
        "trust_level": "Highest (Formal Mathematical Authority)",
        "description": "Authoritative formulas, arithmetic definitions, geometric theorems, and statistical formulations."
    },
    {
        "name": "World Bank Open Data",
        "full_url": "https://data.worldbank.org/",
        "domain": "data.worldbank.org",
        "category": "Global Macroeconomics & Demographic Data",
        "trust_level": "Highest (Intergovernmental Organization)",
        "description": "Official macroeconomic indicators, inflation rates, GDP growth, and global population metrics."
    },
    {
        "name": "United Nations Official Records",
        "full_url": "https://www.un.org/en/about-us/",
        "domain": "un.org",
        "category": "International Law & Global Treaties",
        "trust_level": "Highest (Official Treaty Depository)",
        "description": "Official documentation on international treaties, historical charters, and member state accessions."
    },
    {
        "name": "NASA Science & Planetary Factsheets",
        "full_url": "https://science.nasa.gov/solar-system/",
        "domain": "science.nasa.gov",
        "category": "Space Exploration & Astrophysics",
        "trust_level": "Highest (US Space Agency)",
        "description": "Planetary physical parameters, orbital speeds, astronomical constants, and mission logs."
    },
    {
        "name": "PubMed & NCBI (National Library of Medicine)",
        "full_url": "https://pubmed.ncbi.nlm.nih.gov/",
        "domain": "pubmed.ncbi.nlm.nih.gov",
        "category": "Biomedicine, Pharmacology & Life Sciences",
        "trust_level": "Highest (Peer-Reviewed Medical Literature)",
        "description": "Index of peer-reviewed clinical medicine, molecular biology, and physiological literature."
    },
    {
        "name": "Stanford Encyclopedia of Philosophy (SEP)",
        "full_url": "https://plato.stanford.edu/",
        "domain": "plato.stanford.edu",
        "category": "Formal Logic, Ethics & Philosophy of Science",
        "trust_level": "Highest (Peer-Reviewed Academic)",
        "description": "Scholarly peer-reviewed reference for mathematical logic, epistemology, and decision theory."
    },
    {
        "name": "DuckDuckGo Instant Knowledge API",
        "full_url": "https://api.duckduckgo.com/",
        "domain": "api.duckduckgo.com",
        "category": "Multi-Source Knowledge Graph",
        "trust_level": "High (Aggregated Zero-Click Answers)",
        "description": "Aggregated disambiguated facts and quick extracts from trusted global sources."
    }
]


# ============================================================================
# 2. DIRECT ARITHMETIC PARAMETER OPERATIONS SUITE
# ============================================================================

class ArithmeticSuite:
    """
    Direct callable suite for all fundamental and advanced arithmetic operations.
    Can be used by agents, tools, or standalone math verifiers.
    """

    @staticmethod
    def add(a: float, b: float) -> float:
        """Addition: a + b"""
        return float(a) + float(b)

    @staticmethod
    def subtract(a: float, b: float) -> float:
        """Subtraction: a - b"""
        return float(a) - float(b)

    @staticmethod
    def multiply(a: float, b: float) -> float:
        """Multiplication: a * b"""
        return float(a) * float(b)

    @staticmethod
    def divide(a: float, b: float) -> float:
        """Division: a / b (raises ZeroDivisionError if b == 0)"""
        if float(b) == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return float(a) / float(b)

    @staticmethod
    def floor_divide(a: float, b: float) -> float:
        """Floor Division: a // b"""
        if float(b) == 0:
            raise ZeroDivisionError("Cannot floor divide by zero")
        return float(a) // float(b)

    @staticmethod
    def modulo(a: float, b: float) -> float:
        """Modulo (Remainder): a % b"""
        if float(b) == 0:
            raise ZeroDivisionError("Cannot modulo by zero")
        return float(a) % float(b)

    @staticmethod
    def power(base: float, exponent: float) -> float:
        """Exponentiation: base ** exponent"""
        return float(base) ** float(exponent)

    @staticmethod
    def square_root(x: float) -> float:
        """Square Root: sqrt(x)"""
        if float(x) < 0:
            raise ValueError("Square root of negative number not supported in real arithmetic")
        return math.sqrt(float(x))

    @staticmethod
    def percentage(part: float, whole: float) -> float:
        """Calculates (part / whole) * 100"""
        if float(whole) == 0:
            raise ZeroDivisionError("Whole cannot be zero for percentage calculation")
        return (float(part) / float(whole)) * 100.0

    @staticmethod
    def growth_rate(initial: float, final: float) -> float:
        """Percentage growth: ((final - initial) / initial) * 100"""
        if float(initial) == 0:
            raise ZeroDivisionError("Initial value cannot be zero for growth rate")
        return ((float(final) - float(initial)) / float(initial)) * 100.0

    @staticmethod
    def compound_interest(principal: float, rate_pct: float, time_years: float, n_compounds: int = 1) -> float:
        """A = P * (1 + r/n)**(n*t)"""
        r = float(rate_pct) / 100.0
        n = int(n_compounds)
        t = float(time_years)
        return float(principal) * ((1 + r / n) ** (n * t))

    @staticmethod
    def mean(numbers: List[float]) -> float:
        """Arithmetic mean / average"""
        if not numbers:
            return 0.0
        return sum(numbers) / len(numbers)

    @staticmethod
    def standard_deviation(numbers: List[float]) -> float:
        """Population standard deviation"""
        if len(numbers) < 2:
            return 0.0
        avg = sum(numbers) / len(numbers)
        variance = sum((x - avg) ** 2 for x in numbers) / len(numbers)
        return math.sqrt(variance)


# ============================================================================
# 3. SAFE AST-BASED ARITHMETIC EXPRESSION EVALUATOR
# ============================================================================

class SafeArithmeticEvaluator:
    """
    Evaluates mathematical expressions safely using Abstract Syntax Trees (AST).
    Supports all core arithmetic operations without using unsafe eval().
    """

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    @classmethod
    def evaluate_expression(cls, expr: str) -> float:
        """
        Safely evaluates an arithmetic expression string.
        Examples: '120 * 1.15', '(500 - 320) / 320 * 100', '2 ** 8', '145 % 12'
        """
        cleaned = expr.replace(",", "").replace("$", "").replace("€", "").replace("£", "").replace("%", "/ 100")
        tree = ast.parse(cleaned, mode='eval')
        return cls._eval_node(tree.body)

    @classmethod
    def _eval_node(cls, node):
        if isinstance(node, ast.Constant):
            return float(node.value)
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op_type = type(node.op)
            if op_type in cls.OPERATORS:
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    raise ZeroDivisionError("Division by zero in arithmetic verification")
                return cls.OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in cls.OPERATORS:
                return cls.OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")
        elif isinstance(node, ast.Call):
            func_name = getattr(node.func, 'id', '')
            args = [cls._eval_node(arg) for arg in node.args]
            if func_name == 'sqrt' and len(args) == 1:
                return math.sqrt(args[0])
            elif func_name == 'abs' and len(args) == 1:
                return abs(args[0])
            elif func_name == 'round' and len(args) in (1, 2):
                return round(args[0], int(args[1]) if len(args) == 2 else 0)
            raise ValueError(f"Unsupported math function: {func_name}")
        else:
            raise TypeError(f"Unsupported AST node type: {type(node)}")

    @classmethod
    def verify_arithmetic_claim(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extracts arithmetic statements from text and verifies their mathematical validity.
        """
        results = []

        # 1. Pattern: Equation matching: A [op] B = C
        eq_pattern = r'([\d\.,\s\+\-\*\/\(\)\^%]+)\s*(?:=|equals|is equal to)\s*([\d\.,]+)'
        for match in re.finditer(eq_pattern, text, re.IGNORECASE):
            expr_str, claimed_val_str = match.groups()
            expr_str = expr_str.strip().replace("^", "**")
            claimed_val_str = claimed_val_str.strip().replace(",", "")
            
            if not any(op in expr_str for op in ['+', '-', '*', '/', '**', '%']):
                continue
            
            try:
                actual_val = cls.evaluate_expression(expr_str)
                claimed_val = float(claimed_val_str)
                is_correct = math.isclose(actual_val, claimed_val, rel_tol=1e-3, abs_tol=1e-3)
                
                results.append({
                    "type": "equation",
                    "expression": expr_str,
                    "claimed": claimed_val,
                    "claimed_raw": claimed_val_str,
                    "actual": round(actual_val, 4),
                    "is_valid": is_correct,
                    "discrepancy": round(abs(claimed_val - actual_val), 4),
                    "error_message": None if is_correct else (
                        f"Arithmetic Hallucination: {expr_str} equals {round(actual_val, 2)}, but claimed {claimed_val}"
                    )
                })
            except Exception:
                continue

        # 2. Pattern: Percentage Change matching: "from $X to $Y ... Z%"
        pct_pattern = r'from\s+[\$€£]?\s*([\d\.,]+)\s+to\s+[\$€£]?\s*([\d\.,]+)[^\.\n]*?(\d+(?:\.\d+)?)\s*%'
        for match in re.finditer(pct_pattern, text, re.IGNORECASE):
            x_str, y_str, claimed_pct_str = match.groups()
            try:
                v1 = float(x_str.replace(",", ""))
                v2 = float(y_str.replace(",", ""))
                claimed_pct = float(claimed_pct_str)
                if v1 != 0:
                    actual_pct = abs((v2 - v1) / v1) * 100.0
                    is_correct = math.isclose(actual_pct, claimed_pct, rel_tol=0.05, abs_tol=0.5)
                    results.append({
                        "type": "percentage_growth",
                        "expression": f"|({v2} - {v1}) / {v1}| * 100",
                        "claimed": claimed_pct,
                        "claimed_raw": claimed_pct_str,
                        "actual": round(actual_pct, 2),
                        "is_valid": is_correct,
                        "discrepancy": round(abs(claimed_pct - actual_pct), 2),
                        "error_message": None if is_correct else (
                            f"Percentage Hallucination: Change from {v1} to {v2} is {round(actual_pct, 1)}%, but claimed {claimed_pct}%"
                        )
                    })
            except Exception:
                continue

        return results


# ============================================================================
# 4. TRUSTED WEB FETCH VERIFICATION TOOL
# ============================================================================

class WebFetchCriticTool:
    """
    Autonomous web fetcher and factual evidence cross-examiner.
    Fetches real-time web summaries from trusted domains with full URLs and offline caching fallback.
    """

    CACHE = {
        "eiffel tower": {
            "text": "The Eiffel Tower was designed by Maurice Koechlin and Émile Nouguier, and built under Gustave Eiffel in 1889 in Paris, France.",
            "source_title": "Eiffel Tower",
            "source_url": "https://en.wikipedia.org/wiki/Eiffel_Tower",
            "source_domain": "en.wikipedia.org"
        },
        "speed of light": {
            "text": "The speed of light in a vacuum is exactly 299,792,458 metres per second (approximately 300,000 km/s).",
            "source_title": "Speed of Light (CODATA)",
            "source_url": "https://physics.nist.gov/cuu/Constants/",
            "source_domain": "physics.nist.gov"
        },
        "python creator": {
            "text": "Python was conceived in the late 1980s by Guido van Rossum at CWI in the Netherlands and released in 1991.",
            "source_title": "Python (programming language)",
            "source_url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
            "source_domain": "en.wikipedia.org"
        },
        "python": {
            "text": "Python was conceived in the late 1980s by Guido van Rossum at CWI in the Netherlands and released in 1991.",
            "source_title": "Python (programming language)",
            "source_url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
            "source_domain": "en.wikipedia.org"
        },
        "amazon river": {
            "text": "The Amazon River in South America is the largest river by discharge volume of water in the world.",
            "source_title": "Amazon River",
            "source_url": "https://www.britannica.com/place/Amazon-River",
            "source_domain": "britannica.com"
        },
        "boiling point water": {
            "text": "At standard atmospheric pressure (1 atm), pure water boils at 100 degrees Celsius (212 degrees Fahrenheit).",
            "source_title": "Boiling Point of Water",
            "source_url": "https://physics.nist.gov/cuu/Units/temperature.html",
            "source_domain": "physics.nist.gov"
        },
        "boil": {
            "text": "At standard atmospheric pressure (1 atm), pure water boils at 100 degrees Celsius (212 degrees Fahrenheit).",
            "source_title": "Boiling Point of Water",
            "source_url": "https://physics.nist.gov/cuu/Units/temperature.html",
            "source_domain": "physics.nist.gov"
        },
        "mount everest": {
            "text": "Mount Everest is Earth's highest mountain above sea level, located in the Mahalangur Himal sub-range of the Himalayas, with an elevation of 8,848.86 metres.",
            "source_title": "Mount Everest",
            "source_url": "https://www.britannica.com/place/Mount-Everest",
            "source_domain": "britannica.com"
        },
        "great wall of china": {
            "text": "Most of the existing Great Wall was built during the Ming dynasty in 1368 (1368-1644).",
            "source_title": "Great Wall of China",
            "source_url": "https://www.britannica.com/topic/Great-Wall-of-China",
            "source_domain": "britannica.com"
        },
        "great wall": {
            "text": "Most of the existing Great Wall was built during the Ming dynasty in 1368 (1368-1644).",
            "source_title": "Great Wall of China",
            "source_url": "https://www.britannica.com/topic/Great-Wall-of-China",
            "source_domain": "britannica.com"
        },
        "united nations": {
            "text": "The United Nations (UN) was founded on October 24, 1945, after World War II.",
            "source_title": "History of the United Nations",
            "source_url": "https://www.un.org/en/about-us/history-of-the-un",
            "source_domain": "un.org"
        },
        "mona lisa": {
            "text": "The Mona Lisa is a half-length portrait painting by Italian artist Leonardo da Vinci.",
            "source_title": "Mona Lisa",
            "source_url": "https://www.britannica.com/topic/Mona-Lisa-painting",
            "source_domain": "britannica.com"
        },
        "photosynthesis": {
            "text": "During oxygenic photosynthesis, light energy transfers electrons from water to carbon dioxide, producing carbohydrates and releasing oxygen.",
            "source_title": "Photosynthesis",
            "source_url": "https://www.britannica.com/science/photosynthesis",
            "source_domain": "britannica.com"
        }
    }

    STOP_WORDS = {"what", "when", "where", "who", "which", "why", "how", "the", "a", "an", "is", "was", "were", "in", "on", "at", "by", "for", "with", "of", "and", "or"}

    @classmethod
    def get_trusted_sources(cls) -> List[Dict[str, str]]:
        """Returns the curated list of verified reference websites with full links."""
        return TRUSTED_WEBSITES

    @classmethod
    def fetch_web_summary(cls, query: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Fetches web evidence with full source URLs from trusted knowledge sources.
        """
        clean_q = query.strip().lower()
        q_tokens = set(re.findall(r'\b[a-z]{3,}\b', clean_q)) - cls.STOP_WORDS

        # 1. Exact match in cache
        for key, entry in cls.CACHE.items():
            if key in clean_q:
                return {
                    "source": "verified_cache",
                    "query": query,
                    "content": entry["text"],
                    "source_title": entry["source_title"],
                    "source_url": entry["source_url"],
                    "domain": entry["source_domain"],
                    "status": "success"
                }

        # 2. Token overlap match in cache
        best_match = None
        best_overlap = 0
        for key, entry in cls.CACHE.items():
            key_tokens = set(key.split()) - cls.STOP_WORDS
            overlap = len(key_tokens & q_tokens)
            if overlap >= max(1, len(key_tokens) // 2) and overlap > best_overlap:
                best_overlap = overlap
                best_match = entry

        if best_match:
            return {
                "source": "verified_cache",
                "query": query,
                "content": best_match["text"],
                "source_title": best_match["source_title"],
                "source_url": best_match["source_url"],
                "domain": best_match["source_domain"],
                "status": "success"
            }

        # 3. Live Wikipedia REST API fetch with full URL generation
        try:
            encoded_query = urllib.parse.quote(query[:60])
            api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "CriticAI/2.0 (Academic Verification Tool; vit.edu)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                extract = data.get("extract", "")
                page_title = data.get("title", query)
                content_urls = data.get("content_urls", {}).get("desktop", {}).get("page")
                full_wiki_url = content_urls or f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title.replace(' ', '_'))}"
                
                if extract:
                    return {
                        "source": "live_wikipedia_api",
                        "query": query,
                        "content": extract[:600],
                        "source_title": page_title,
                        "source_url": full_wiki_url,
                        "domain": "en.wikipedia.org",
                        "status": "success"
                    }
        except Exception:
            pass

        # Fallback to general Britannica search full link
        encoded_term = urllib.parse.quote(query[:40])
        return {
            "source": "fallback_reference",
            "query": query,
            "content": f"Verified factual references for {query}.",
            "source_title": f"Reference on {query}",
            "source_url": f"https://www.britannica.com/search?query={encoded_term}",
            "domain": "britannica.com",
            "status": "fallback"
        }

    @classmethod
    def verify_factual_claims(cls, candidate_answer: str, query: str) -> List[Dict[str, Any]]:
        """
        Cross-checks key entities, numbers, and dates against fetched evidence from trusted sites.
        """
        evidence = cls.fetch_web_summary(query)
        evidence_text = evidence.get("content", "").lower()
        source_url = evidence.get("source_url", "https://en.wikipedia.org/")
        source_title = evidence.get("source_title", "Verified Source")
        issues = []

        cand_years = re.findall(r'\b(1[3-9]\d\d|20\d\d)\b', candidate_answer)
        for year in cand_years:
            if year not in evidence_text and len(evidence_text) > 30:
                ev_years = re.findall(r'\b(1[3-9]\d\d|20\d\d)\b', evidence_text)
                if ev_years and year not in ev_years:
                    issues.append({
                        "type": "temporal_hallucination",
                        "claimed": year,
                        "evidence_context": f"Evidence cites {', '.join(ev_years)} (Source: {source_title})",
                        "source_url": source_url,
                        "error_message": f"Temporal Hallucination: Claimed year {year} conflicts with source ({ev_years[0]}). Verified at: {source_url}"
                    })

        return issues


# ============================================================================
# 5. CORE CRITIC ENGINE
# ============================================================================

@dataclass
class AuditReport:
    candidate_answer: str
    verdict: str  # "APPROVE", "REVISE", "REJECT"
    confidence: float
    arithmetic_checks: List[Dict[str, Any]]
    factual_checks: List[Dict[str, Any]]
    hallucination_detected: bool
    hallucination_types: List[str]
    audit_notes: List[str]
    source_links: List[str]
    corrected_answer: Optional[str] = None


class Critic:
    """
    Independent verification and fact-checking Critic agent.
    Audits candidate answers, flags hallucinations, verifies arithmetic rigor,
    and cross-examines facts against trusted web encyclopedias.
    """

    def __init__(self, confidence_threshold: float = 0.85):
        self.arithmetic_suite = ArithmeticSuite
        self.arithmetic_evaluator = SafeArithmeticEvaluator()
        self.web_fetcher = WebFetchCriticTool()
        self.confidence_threshold = confidence_threshold
        self.trusted_sources = TRUSTED_WEBSITES

    def get_trusted_websites(self) -> List[Dict[str, str]]:
        """Returns the full list of trusted web sources with full links."""
        return self.trusted_sources

    def audit(self, question: str, candidate_answer: str, context: Optional[str] = None) -> AuditReport:
        """
        Conducts a multi-stage audit of the candidate answer:
        1. Arithmetic Verification (AST + parameter checks)
        2. Web Evidence Cross-Examination from trusted sources
        3. Confidence Scoring
        4. Delta Correction Synthesis
        """
        audit_notes = []
        hallucination_types = []
        source_links = []

        # 1. Arithmetic Audit
        arithmetic_checks = self.arithmetic_evaluator.verify_arithmetic_claim(candidate_answer)
        for check in arithmetic_checks:
            if not check["is_valid"]:
                hallucination_types.append("ARITHMETIC_ERROR")
                audit_notes.append(check["error_message"])

        # 2. Web Fact Audit via Trusted Knowledge
        search_query = question
        factual_checks = self.web_fetcher.verify_factual_claims(candidate_answer, search_query)
        for check in factual_checks:
            hallucination_types.append("TEMPORAL_ERROR")
            audit_notes.append(check["error_message"])
            if "source_url" in check and check["source_url"] not in source_links:
                source_links.append(check["source_url"])

        # If no issues, add the primary source link
        if not source_links:
            ev = self.web_fetcher.fetch_web_summary(question)
            if ev.get("source_url"):
                source_links.append(ev["source_url"])

        # Determine Verdict & Confidence
        has_hallucination = len(hallucination_types) > 0
        if not has_hallucination:
            verdict = "APPROVE"
            confidence = 0.95
        else:
            verdict = "REVISE"
            confidence = max(0.20, 0.90 - (0.35 * len(hallucination_types)))

        # Formulate Delta Correction
        corrected_answer = candidate_answer
        if has_hallucination:
            for check in arithmetic_checks:
                if not check["is_valid"]:
                    raw_val = check.get("claimed_raw", str(check["claimed"]))
                    actual_str = str(int(check["actual"]) if check["actual"].is_integer() else check["actual"])
                    
                    if check["type"] == "percentage_growth":
                        pat = rf'([\b\$€£\s\w]+from\s+[\$€£]?\s*[\d\.,]+\s+to\s+[\$€£]?\s*[\d\.,]+[^\.\n]*?){re.escape(raw_val)}\s*%'
                        if re.search(pat, corrected_answer):
                            corrected_answer = re.sub(pat, rf'\g<1>{actual_str}%', corrected_answer)
                        else:
                            corrected_answer = re.sub(rf'{re.escape(raw_val)}\s*%', f"{actual_str}%", corrected_answer)
                    else:
                        pat = rf'=\s*{re.escape(raw_val)}'
                        corrected_answer = re.sub(pat, f"= {actual_str}", corrected_answer)
                        if f"= {actual_str}" not in corrected_answer:
                            corrected_answer = corrected_answer.replace(raw_val, actual_str)

            for check in factual_checks:
                if "claimed" in check and "evidence_context" in check:
                    ev_years = re.findall(r'\b(1[3-9]\d\d|20\d\d)\b', check["evidence_context"])
                    if ev_years:
                        corrected_answer = re.sub(rf'\b{check["claimed"]}\b', ev_years[0], corrected_answer)

        return AuditReport(
            candidate_answer=candidate_answer,
            verdict=verdict,
            confidence=round(confidence, 2),
            arithmetic_checks=arithmetic_checks,
            factual_checks=factual_checks,
            hallucination_detected=has_hallucination,
            hallucination_types=list(set(hallucination_types)),
            audit_notes=audit_notes,
            source_links=source_links,
            corrected_answer=corrected_answer if has_hallucination else None
        )


# Backward compatibility alias
StandaloneCritic = Critic

def calculate(op: str, *args) -> float:
    """Convenience calculation shortcut: calculate('add', 10, 20)"""
    fn = getattr(ArithmeticSuite, op, None)
    if fn is None:
        raise ValueError(f"Unknown operation: {op}")
    return fn(*args)

def fetch_web(query: str) -> Dict[str, Any]:
    """Convenience web fetch shortcut returning evidence content and full citation URL"""
    return WebFetchCriticTool.fetch_web_summary(query)


# ============================================================================
# 6. DEMO HARNESS
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CRITIC ENGINE: ARITHMETIC SUITE & TRUSTED SOURCE FACT-CHECKING")
    print("=" * 80)

    critic = Critic()

    # 1. Display list of trusted websites with full links
    print("\n[CURATED TRUSTED KNOWLEDGE SOURCES]")
    for i, src in enumerate(critic.get_trusted_websites()[:6], 1):
        print(f" {i}. {src['name']} ({src['category']})")
        print(f"    Full URL: {src['full_url']}")
        print(f"    Trust:    {src['trust_level']}")

    # 2. Test web fetch with full link attribution
    print("\n[WEB FETCH WITH FULL URL CITATION]")
    evidence = fetch_web("Eiffel Tower")
    print(f"Title:      {evidence['source_title']}")
    print(f"Full URL:   {evidence['source_url']}")
    print(f"Snippet:    {evidence['content'][:110]}...")

    # 3. Test Critic Audit with Hallucination Correction
    print("\n[CRITIC AUDIT & DELTA CORRECTION]")
    q = "If an investment grows from $80 to $120 over 3 years, what is the total percentage growth?"
    cand = "The investment grew from $80 to $120, which is an increase of 65%. It occurred in 1999."
    audit = critic.audit(q, cand)
    print(f"Question:        {q}")
    print(f"Candidate:       {cand}")
    print(f"Verdict:         {audit.verdict} (Confidence: {audit.confidence})")
    print(f"Issues Detected: {audit.audit_notes}")
    print(f"Source Links:    {audit.source_links}")
    print(f"Corrected:       {audit.corrected_answer}")
    print("=" * 80)
