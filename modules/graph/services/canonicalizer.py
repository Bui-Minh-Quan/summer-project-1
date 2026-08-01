"""
Service for Entity Name Normalization, Validation, and Deterministic Hash Generation.
"""

import hashlib
import re

# Predefined VN30 tickers for strict STOCK validation. 
# This can be expanded later by querying the vnstock API if needed.
VN30_TICKERS = {
    "ACB", "BID", "CTG", "DGC", "FPT", "GAS", "GVR", "HDB", "HPG", "LPB", 
    "MBB", "MSN", "MWG", "PLX", "SAB", "SHB", "SSB", "SSI", "STB", "TCB", 
    "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VPL", "VRE"
}

class GraphCanonicalizer:
    
    @staticmethod
    def is_valid_entity_name(name: str) -> bool:
        """
        Check if the name is valid. 
        It must not be empty and the first character must be an alphabet letter.
        """
        if not name or not name.strip():
            return False
        
        # Check if the first non-whitespace character is a letter
        first_char = name.strip()[0]
        return first_char.isalpha()

    @staticmethod
    def normalize_node(name: str, entity_type: str) -> tuple[str, str]:
        """
        Normalizes the entity name and validates its type.
        Returns a tuple of (normalized_name, validated_type).
        """
        # 1. Standardize whitespace
        clean_name = " ".join(name.strip().split())
        
        # 2. Strict STOCK handling
        if entity_type == "STOCK":
            upper_name = clean_name.upper()
            if upper_name in VN30_TICKERS:
                return upper_name, "STOCK"
            else:
                # Downgrade to OTHER and format with uppercase first letter
                downgraded_name = clean_name[0].upper() + clean_name[1:]
                return downgraded_name, "OTHER"
        
        # 3. Standard handling for all other types
        normalized_name = clean_name[0].upper() + clean_name[1:]
        return normalized_name, entity_type

    @staticmethod
    def normalize_relation(relation: str) -> str:
        """
        Cleans the relation/predicate text for the graph edge.
        """
        # Collapse whitespace, lowercase, and remove trailing punctuation
        clean_rel = " ".join(relation.strip().lower().split())
        return re.sub(r'[.,;:]+$', '', clean_rel)

    @staticmethod
    def generate_node_id(name: str, entity_type: str) -> str:
        """
        Generates a deterministic SHA-256 hash for a node.
        Uses lowercased names to ensure case-insensitive idempotency.
        """
        raw_key = f"NODE|{entity_type.upper()}|{name.lower()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_edge_id(subject_id: str, relation: str, object_id: str, doc_id: str) -> str:
        """
        Generates a deterministic SHA-256 hash for an edge.
        Incorporating doc_id ensures we don't duplicate edges from the same article.
        """
        clean_relation = GraphCanonicalizer.normalize_relation(relation)
        raw_key = f"EDGE|{subject_id}|{clean_relation}|{object_id}|{doc_id}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()