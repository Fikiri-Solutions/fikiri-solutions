#!/usr/bin/env python3
"""
Fikiri Solutions - Strategic Feature Flag System
Smart feature flags for heavy dependencies with fallbacks.
"""

import os
import json
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from enum import Enum

class FeatureLevel(Enum):
    """Feature capability levels."""
    LIGHTWEIGHT = "lightweight"      # Pure Python, no heavy deps
    ENHANCED = "enhanced"            # Light ML (scikit-learn)
    ADVANCED = "advanced"            # Heavy ML (TensorFlow, PyTorch)
    FULL_AI = "full_ai"              # All AI capabilities

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
                "heavy_deps": ["tensorflow", "torch", "scikit-learn"]
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
                print(f"✅ Loaded feature flags from {self.config_path}")
        except Exception as e:
            print(f"⚠️  Could not load feature flags: {e}")
    
    def save_config(self):
        """Save feature flags to config file."""
        try:
            self.config_path.parent.mkdir(exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.flags, f, indent=2, default=str)
            print(f"✅ Saved feature flags to {self.config_path}")
        except Exception as e:
            print(f"❌ Could not save feature flags: {e}")
    
    def _check_heavy_dependencies(self):
        """Check which heavy dependencies are available."""
        heavy_deps = {
            "openai": self._check_import("openai"),
            "scikit-learn": self._check_import("sklearn"),
            "sentence-transformers": self._check_import("sentence_transformers"),
            "faiss-cpu": self._check_import("faiss"),
            "beautifulsoup4": self._check_import("bs4"),
            "transformers": self._check_import("transformers"),
            "torch": self._check_import("torch"),
            "tensorflow": self._check_import("tensorflow"),
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
            # Handle TensorFlow AVX errors and other import issues gracefully
            if "tensorflow" in module_name.lower():
                print(f"⚠️  TensorFlow compatibility issue detected, skipping {module_name}")
                return False
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
            print(f"✅ Enabled feature: {feature_name}")
    
    def disable_feature(self, feature_name: str):
        """Disable a feature."""
        if feature_name in self.flags:
            self.flags[feature_name]["enabled"] = False
            print(f"❌ Disabled feature: {feature_name}")
    
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
        print(f"🎯 Set strategic mode: {mode} ({target_level.value})")
    
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
                print(f"🚀 Using heavy implementation for {feature_name}")
                return heavy_func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️  Heavy implementation failed for {feature_name}: {e}")
                if self.flags[feature_name].get("fallback", False):
                    print(f"🔄 Falling back to lightweight implementation")
                    return fallback_func(*args, **kwargs)
                else:
                    raise
        else:
            print(f"⚡ Using lightweight implementation for {feature_name}")
            return fallback_func(*args, **kwargs)
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report."""
        return {
            "feature_flags": self.flags,
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
                print(f"⚠️  Feature {feature_name} is disabled")
                return None
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test the feature flag system
    print("🧪 Testing Strategic Feature Flag System")
    print("=" * 60)
    
    flags = FeatureFlags()
    
    # Test basic functionality
    print("Testing basic functionality...")
    print(f"✅ Gmail integration enabled: {flags.is_enabled('gmail_integration')}")
    print(f"✅ AI responses enabled: {flags.is_enabled('ai_email_responses')}")
    print(f"✅ Advanced NLP enabled: {flags.is_enabled('advanced_nlp')}")
    
    # Test dependency checking
    print(f"\nTesting dependency status...")
    for dep, available in flags._heavy_deps_status.items():
        status = "✅" if available else "❌"
        print(f"{status} {dep}: {'Available' if available else 'Not available'}")
    
    # Test strategic recommendations
    print(f"\nTesting strategic recommendations...")
    recommendations = flags.get_strategic_recommendations()
    print(f"✅ Current capabilities: {len(recommendations['current_capabilities'])}")
    print(f"✅ Available upgrades: {len(recommendations['available_upgrades'])}")
    print(f"✅ Missing dependencies: {len(recommendations['missing_dependencies'])}")
    
    # Test strategic modes
    print(f"\nTesting strategic modes...")
    flags.set_strategic_mode("balanced")
    print(f"✅ Set to balanced mode")
    
    # Test status report
    print(f"\nTesting status report...")
    status = flags.get_status_report()
    print(f"✅ Total features: {status['total_features']}")
    print(f"✅ Enabled features: {status['enabled_features']}")
    print(f"✅ Heavy deps available: {status['heavy_deps_available']}")
    
    print("\n🎉 All feature flag tests completed!")

