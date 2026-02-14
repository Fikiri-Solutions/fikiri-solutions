#!/usr/bin/env python3
"""
Fikiri Solutions - Strategic Feature Flag System
Smart feature flags for heavy dependencies with fallbacks.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

class FeatureLevel(Enum):
    """Feature capability levels."""
    LIGHTWEIGHT = "lightweight"      # Pure Python, no heavy deps
    ENHANCED = "enhanced"            # Light ML (scikit-learn)
    ADVANCED = "advanced"            # Heavy ML (PyTorch, scikit-learn)
    FULL_AI = "full_ai"              # All AI capabilities

SKIP_HEAVY_CHECKS = os.getenv("SKIP_HEAVY_DEP_CHECKS", "false").lower() == "true"


class FeatureFlags:
    """Strategic feature flag manager."""
    
    def __init__(self, config_path: str = "data/feature_flags.json"):
        """Initialize feature flags."""
        self.config_path = Path(config_path)
        self.flags = self._load_default_flags()
        self.load_config()
        
        # Track heavy dependency status
        self._heavy_deps_status = {}
        self._check_heavy_dependencies()
    
    def _load_default_flags(self) -> Dict[str, Any]:
        """Load default feature flags."""
        return {
            # Core features (always enabled)
            "gmail_integration": {"enabled": True, "level": FeatureLevel.LIGHTWEIGHT},
            "email_parsing": {"enabled": True, "level": FeatureLevel.LIGHTWEIGHT},
            "crm_basic": {"enabled": True, "level": FeatureLevel.LIGHTWEIGHT},
            "config_management": {"enabled": True, "level": FeatureLevel.LIGHTWEIGHT},
            
            # AI features (strategic)
            "ai_email_responses": {
                "enabled": True, 
                "level": FeatureLevel.ENHANCED,
                "fallback": True,
                "heavy_deps": ["openai"]
            },
            "ml_lead_scoring": {
                "enabled": True,
                "level": FeatureLevel.ENHANCED, 
                "fallback": True,
                "heavy_deps": ["scikit-learn"]
            },
            "vector_search": {
                "enabled": True,
                "level": FeatureLevel.ENHANCED,
                "fallback": True,
                "heavy_deps": ["sentence-transformers", "faiss-cpu"]
            },
            "document_processing": {
                "enabled": True,
                "level": FeatureLevel.ENHANCED,
                "fallback": True,
                "heavy_deps": ["beautifulsoup4"]
            },
            
            # Advanced features (optional)
            "advanced_nlp": {
                "enabled": False,
                "level": FeatureLevel.ADVANCED,
                "fallback": True,
                "heavy_deps": ["transformers", "torch"]
            },
            "computer_vision": {
                "enabled": False,
                "level": FeatureLevel.ADVANCED,
                "fallback": True,
                "heavy_deps": ["opencv-python", "pillow"]
            },
            "custom_model_training": {
                "enabled": False,
                "level": FeatureLevel.FULL_AI,
                "fallback": False,
                "heavy_deps": ["torch", "scikit-learn"]
            }
        }
    
    def load_config(self):
        """Load feature flags from config file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    # Update flags with config data
                    for flag_name, flag_config in config_data.items():
                        if flag_name in self.flags:
                            self.flags[flag_name].update(flag_config)
                logger.info("Loaded feature flags from %s", self.config_path)
        except Exception as e:
            logger.warning("Could not load feature flags: %s", e)
    
    def save_config(self):
        """Save feature flags to config file."""
        try:
            self.config_path.parent.mkdir(exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.flags, f, indent=2, default=str)
            logger.info("Saved feature flags to %s", self.config_path)
        except Exception as e:
            logger.error("Could not save feature flags: %s", e)
    
    def _check_heavy_dependencies(self):
        """Check which heavy dependencies are available."""
        if SKIP_HEAVY_CHECKS:
            self._heavy_deps_status = {
                "openai": False,
                "scikit-learn": False,
                "sentence-transformers": False,
                "faiss-cpu": False,
                "beautifulsoup4": True,
                "transformers": False,
                "torch": False,
                "opencv-python": False,
                "pillow": False
            }
            self._auto_adjust_features()
            return
        
        heavy_deps = {
            "openai": self._check_import("openai"),
            "scikit-learn": False,  # Removed for lightweight operation
            "sentence-transformers": self._check_import("sentence_transformers"),
            "faiss-cpu": self._check_import("faiss"),
            "beautifulsoup4": self._check_import("bs4"),
            "transformers": self._check_import("transformers"),
            "torch": self._check_import("torch"),
            "opencv-python": self._check_import("cv2"),
            "pillow": self._check_import("PIL")
        }
        
        self._heavy_deps_status = heavy_deps
        
        # Auto-adjust feature levels based on available dependencies
        self._auto_adjust_features()
    
    def _check_import(self, module_name: str) -> bool:
        """Check if a module can be imported."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.warning("Import check failed for %s: %s", module_name, e)
            return False
    
    def _auto_adjust_features(self):
        """Automatically adjust feature levels based on available dependencies."""
        for flag_name, flag_config in self.flags.items():
            heavy_deps = flag_config.get("heavy_deps", [])
            if heavy_deps:
                # Check if all required dependencies are available
                all_available = all(
                    self._heavy_deps_status.get(dep, False) 
                    for dep in heavy_deps
                )
                
                if not all_available and flag_config.get("fallback", False):
                    # Downgrade to lightweight if fallback is available
                    flag_config["effective_level"] = FeatureLevel.LIGHTWEIGHT
                    flag_config["downgraded"] = True
                else:
                    flag_config["effective_level"] = flag_config["level"]
                    flag_config["downgraded"] = False
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return self.flags.get(feature_name, {}).get("enabled", False)
    
    def get_level(self, feature_name: str) -> FeatureLevel:
        """Get the effective level of a feature."""
        flag_config = self.flags.get(feature_name, {})
        return flag_config.get("effective_level", flag_config.get("level", FeatureLevel.LIGHTWEIGHT))
    
    def can_use_heavy_deps(self, feature_name: str) -> bool:
        """Check if heavy dependencies are available for a feature."""
        flag_config = self.flags.get(feature_name, {})
        heavy_deps = flag_config.get("heavy_deps", [])
        
        if not heavy_deps:
            return True
        
        return all(
            self._heavy_deps_status.get(dep, False) 
            for dep in heavy_deps
        )
    
    def enable_feature(self, feature_name: str, level: Optional[FeatureLevel] = None):
        """Enable a feature with optional level specification."""
        if feature_name in self.flags:
            self.flags[feature_name]["enabled"] = True
            if level:
                self.flags[feature_name]["level"] = level
            self._auto_adjust_features()
            logger.info("Enabled feature: %s", feature_name)
    
    def disable_feature(self, feature_name: str):
        """Disable a feature."""
        if feature_name in self.flags:
            self.flags[feature_name]["enabled"] = False
            logger.info("Disabled feature: %s", feature_name)
    
    def set_strategic_mode(self, mode: str):
        """Set strategic mode for all features."""
        modes = {
            "minimal": FeatureLevel.LIGHTWEIGHT,
            "balanced": FeatureLevel.ENHANCED,
            "advanced": FeatureLevel.ADVANCED,
            "full": FeatureLevel.FULL_AI
        }
        
        target_level = modes.get(mode, FeatureLevel.ENHANCED)
        
        for flag_name, flag_config in self.flags.items():
            if flag_config.get("enabled", False):
                flag_config["level"] = target_level
        
        self._auto_adjust_features()
        logger.info("Set strategic mode: %s (%s)", mode, target_level.value)
    
    def get_strategic_recommendations(self) -> Dict[str, Any]:
        """Get strategic recommendations based on current setup."""
        recommendations = {
            "current_capabilities": [],
            "available_upgrades": [],
            "missing_dependencies": [],
            "performance_impact": "low"
        }
        
        # Analyze current capabilities
        for flag_name, flag_config in self.flags.items():
            if flag_config.get("enabled", False):
                level = flag_config.get("effective_level", FeatureLevel.LIGHTWEIGHT)
                recommendations["current_capabilities"].append({
                    "feature": flag_name,
                    "level": level.value,
                    "downgraded": flag_config.get("downgraded", False)
                })
        
        # Find available upgrades
        for flag_name, flag_config in self.flags.items():
            if flag_config.get("enabled", False) and flag_config.get("downgraded", False):
                recommendations["available_upgrades"].append({
                    "feature": flag_name,
                    "required_deps": flag_config.get("heavy_deps", []),
                    "target_level": flag_config.get("level", FeatureLevel.LIGHTWEIGHT).value
                })
        
        # Find missing dependencies
        for dep, available in self._heavy_deps_status.items():
            if not available:
                recommendations["missing_dependencies"].append(dep)
        
        return recommendations
    
    def execute_with_fallback(self, feature_name: str, heavy_func: Callable, fallback_func: Callable, *args, **kwargs):
        """Execute function with heavy dependencies, fallback to lightweight if needed."""
        if self.is_enabled(feature_name) and self.can_use_heavy_deps(feature_name):
            try:
                logger.info("Using heavy implementation for %s", feature_name)
                return heavy_func(*args, **kwargs)
            except Exception as e:
                logger.warning("Heavy implementation failed for %s: %s", feature_name, e)
                if self.flags[feature_name].get("fallback", False):
                    logger.info("Falling back to lightweight implementation")
                    return fallback_func(*args, **kwargs)
                else:
                    raise
        else:
            logger.info("Using lightweight implementation for %s", feature_name)
            return fallback_func(*args, **kwargs)
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report."""
        # Convert FeatureLevel enums to strings for JSON serialization
        serializable_flags = {}
        for name, config in self.flags.items():
            serializable_config = config.copy()
            if 'level' in serializable_config and isinstance(serializable_config['level'], FeatureLevel):
                serializable_config['level'] = serializable_config['level'].value
            serializable_flags[name] = serializable_config
        
        return {
            "feature_flags": serializable_flags,
            "dependency_status": self._heavy_deps_status,
            "strategic_recommendations": self.get_strategic_recommendations(),
            "total_features": len(self.flags),
            "enabled_features": sum(1 for f in self.flags.values() if f.get("enabled", False)),
            "heavy_deps_available": sum(1 for available in self._heavy_deps_status.values() if available)
        }

# Global feature flags instance
_feature_flags: Optional[FeatureFlags] = None

def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags

def with_feature_flag(feature_name: str):
    """Decorator to conditionally execute code based on feature flags."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            flags = get_feature_flags()
            if flags.is_enabled(feature_name):
                return func(*args, **kwargs)
            else:
                logger.warning("Feature %s is disabled", feature_name)
                return None
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test the feature flag system
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger.info("Testing Strategic Feature Flag System")
    
    flags = FeatureFlags()
    
    # Test basic functionality
    logger.info("Testing basic functionality...")
    logger.info("Gmail integration enabled: %s", flags.is_enabled('gmail_integration'))
    logger.info("AI responses enabled: %s", flags.is_enabled('ai_email_responses'))
    logger.info("Advanced NLP enabled: %s", flags.is_enabled('advanced_nlp'))
    
    # Test dependency checking
    logger.info("Testing dependency status...")
    for dep, available in flags._heavy_deps_status.items():
        status = "✅" if available else "❌"
        logger.info("%s %s: %s", status, dep, "Available" if available else "Not available")
    
    # Test strategic recommendations
    logger.info("Testing strategic recommendations...")
    recommendations = flags.get_strategic_recommendations()
    logger.info("Current capabilities: %s", len(recommendations['current_capabilities']))
    logger.info("Available upgrades: %s", len(recommendations['available_upgrades']))
    logger.info("Missing dependencies: %s", len(recommendations['missing_dependencies']))
    
    # Test strategic modes
    logger.info("Testing strategic modes...")
    flags.set_strategic_mode("balanced")
    logger.info("Set to balanced mode")
    
    # Test status report
    logger.info("Testing status report...")
    status = flags.get_status_report()
    logger.info("Total features: %s", status['total_features'])
    logger.info("Enabled features: %s", status['enabled_features'])
    logger.info("Heavy deps available: %s", status['heavy_deps_available'])
    
    logger.info("All feature flag tests completed!")
