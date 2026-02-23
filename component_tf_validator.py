"""
Component Timeframe Validation Layer
Validates ICT components for correct timeframe origin, type, and values

This module ensures:
1. Components come from the correct timeframe
2. Bullish/bearish types match bias
3. Non-zero and correctly ordered values
4. Early rejection of invalid components
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of component validation"""
    is_valid: bool
    component_type: str
    errors: List[str]
    warnings: List[str]
    
    def log_result(self):
        """Log validation result"""
        if not self.is_valid:
            logger.error(f"❌ {self.component_type} INVALID: {', '.join(self.errors)}")
        elif self.warnings:
            logger.warning(f"⚠️ {self.component_type} warnings: {', '.join(self.warnings)}")
        else:
            logger.debug(f"✅ {self.component_type} valid")


class ComponentTimeframeValidator:
    """
    Validates ICT components for timeframe integrity
    Prevents cross-timeframe contamination
    """
    @staticmethod
    def validate_order_block(
        ob: Any,
        expected_tf: str,
        expected_bias: str
    ) -> ValidationResult:
        """
        Validate Order Block component (DATA-ONLY)

        Checks:
        - Timeframe matches expected (case-insensitive)
        - Bounds exist (schema-safe: zone_low/zone_high OR bottom/top)
        - Non-zero values
        - Correct high/low ordering (high > low)

        NOTE:
        - Bias-based filtering was REMOVED intentionally.
          Bias alignment should be handled in scoring/scenario selection, not in validation.
        """
        errors = []
        warnings = []

        def _norm_tf(x):
            return str(x).strip().lower() if x is not None else None

        def _get(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        ob_type = _get(ob, 'type', None)

        # Schema-safe bounds:
        zone_low = _get(ob, 'zone_low', None)
        zone_high = _get(ob, 'zone_high', None)
        if zone_low is None:
            zone_low = _get(ob, 'bottom', None)
        if zone_high is None:
            zone_high = _get(ob, 'top', None)

        timeframe = _get(ob, 'timeframe', None)

        # Validate timeframe (case-insensitive)
        if _norm_tf(timeframe) != _norm_tf(expected_tf):
            errors.append(f"TF mismatch: expected {expected_tf}, got {timeframe}")

        # Validate non-zero values
        if zone_low is None or zone_low == 0:
            errors.append(f"Invalid zone_low/bottom: {zone_low}")
        if zone_high is None or zone_high == 0:
            errors.append(f"Invalid zone_high/top: {zone_high}")

        # Validate correct ordering
        try:
            if zone_low is not None and zone_high is not None and float(zone_high) <= float(zone_low):
                errors.append(f"Invalid ordering: high ({zone_high}) <= low ({zone_low})")
        except Exception as e:
            errors.append(f"Ordering check failed: {e}")

        if ob_type is None:
            warnings.append("Missing OB type")

        return ValidationResult(
            is_valid=len(errors) == 0,
            component_type="Order Block",
            errors=errors,
            warnings=warnings
        )
    @staticmethod
    def validate_fvg(
        fvg: Any,
        expected_tf: str,
        expected_bias: str
    ) -> ValidationResult:
        """
        Validate FVG (Fair Value Gap) component (DATA-ONLY)

        Checks:
        - Timeframe matches expected (case-insensitive)
        - Non-zero values
        - Correct top/bottom ordering (top > bottom)

        NOTE:
        - Bias-based filtering was REMOVED intentionally.
          Bias alignment belongs to scoring/scenario selection, not validation.
        """
        errors = []
        warnings = []

        def _norm_tf(x):
            return str(x).strip().lower() if x is not None else None

        def _get(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        is_bullish = _get(fvg, 'is_bullish', None)
        bottom = _get(fvg, 'bottom', None)
        top = _get(fvg, 'top', None)
        timeframe = _get(fvg, 'timeframe', None)

        # Validate timeframe (case-insensitive)
        if _norm_tf(timeframe) != _norm_tf(expected_tf):
            errors.append(f"TF mismatch: expected {expected_tf}, got {timeframe}")

        # Validate non-zero values
        if bottom is None or bottom == 0:
            errors.append(f"Invalid bottom: {bottom}")
        if top is None or top == 0:
            errors.append(f"Invalid top: {top}")

        # Validate correct ordering
        try:
            if bottom is not None and top is not None and float(top) <= float(bottom):
                errors.append(f"Invalid ordering: top ({top}) <= bottom ({bottom})")
        except Exception as e:
            errors.append(f"Ordering check failed: {e}")

        # Optional warnings (do not reject)
        if is_bullish is None:
            warnings.append("Missing is_bullish")

        return ValidationResult(
            is_valid=len(errors) == 0,
            component_type="FVG",
            errors=errors,
            warnings=warnings
        )
    @staticmethod
    def validate_liquidity_zone(
        zone: Any,
        expected_tf: str,
        expected_bias: str
    ) -> ValidationResult:
        """
        Validate Liquidity Zone component (DATA-ONLY)

        Checks:
        - Timeframe matches expected (case-insensitive)
        - Price/level exists (supports LiquidityZone.price_level schema)
        - Strength numeric if present
        - zone_type exists (BSL/SSL/etc.) if present

        NOTE:
        - Bias-based filtering is intentionally not enforced here.
        """
        errors = []
        warnings = []

        def _norm_tf(x):
            return str(x).strip().lower() if x is not None else None

        def _get(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        timeframe = _get(zone, 'timeframe', None) or _get(zone, 'tf', None)
        zone_type = _get(zone, 'zone_type', None) or _get(zone, 'type', None)

        # IMPORTANT: LiquidityZone uses price_level
        price = _get(zone, 'price_level', None)
        if price is None:
            price = _get(zone, 'price', None)
        if price is None:
            price = _get(zone, 'level', None)

        strength = _get(zone, 'strength', None)

        # TF validation
        if _norm_tf(timeframe) != _norm_tf(expected_tf):
            errors.append(f"TF mismatch: expected {expected_tf}, got {timeframe}")

        # Price validation
        if price is None or price == 0:
            errors.append(f"Invalid price: {price}")

        # Strength numeric if present
        if strength is not None:
            try:
                float(strength)
            except Exception:
                errors.append(f"Invalid strength: {strength}")

        if not zone_type:
            warnings.append("Missing zone_type")

        return ValidationResult(
            is_valid=len(errors) == 0,
            component_type="Liquidity Zone",
            errors=errors,
            warnings=warnings
        )
    @staticmethod
    def validate_liquidity_sweep(
        sweep: Any,
        expected_tf: str,
        expected_bias: str
    ) -> ValidationResult:
        """
        Validate Liquidity Sweep component (DATA-ONLY)

        Checks:
        - Timestamp, price required
        - sweep_type recommended
        - Strength numeric if present
        - Timeframe check is OPTIONAL (LiquiditySweep does not carry timeframe in this codebase)
          If timeframe missing -> warning (do not reject)

        NOTE:
        - Bias-based filtering was REMOVED intentionally.
          Bias alignment belongs to scoring/scenario selection, not validation.
        """
        errors = []
        warnings = []

        def _get(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        timestamp = _get(sweep, 'timestamp', None)
        price = _get(sweep, 'price', None)
        sweep_type = _get(sweep, 'sweep_type', None) or _get(sweep, 'type', None) or _get(sweep, 'zone_type', None)
        strength = _get(sweep, 'strength', None)

        # OPTIONAL timeframe presence (accept both 'timeframe' / 'tf' if ever added later)
        timeframe = _get(sweep, 'timeframe', None) or _get(sweep, 'tf', None)
        if timeframe is None:
            warnings.append("Missing timeframe on sweep (optional)")

        # Required fields
        if timestamp is None:
            errors.append("Missing timestamp")
        if price is None or price == 0:
            errors.append(f"Invalid price: {price}")
        if not sweep_type:
            warnings.append("Missing sweep_type")

        # Strength numeric if present
        if strength is not None:
            try:
                float(strength)
            except Exception:
                errors.append(f"Invalid strength: {strength}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            component_type="Liquidity Sweep",
            errors=errors,
            warnings=warnings
        )
    @staticmethod
    def validate_displacement(
        displacement: Dict,
        expected_tf: str
    ) -> ValidationResult:
        """
        Validate Displacement component
        
        Checks:
        - Detection flag is boolean
        - Strength is between 0 and 1
        """
        errors = []
        warnings = []
        
        detected = displacement.get('detected', False)
        strength = displacement.get('strength', 0)
        
        # Validate detection flag
        if not isinstance(detected, bool):
            errors.append(f"Invalid detected flag type: {type(detected)}")
        
        # Validate strength
        if not isinstance(strength, (int, float)):
            errors.append(f"Invalid strength type: {type(strength)}")
        elif strength < 0 or strength > 1:
            errors.append(f"Strength out of range [0,1]: {strength}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            component_type="Displacement",
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_structure_break(
        structure: Dict,
        expected_tf: str
    ) -> ValidationResult:
        """
        Validate Structure Break (MSS/BOS) component
        
        Checks:
        - Valid type (MSS, BOS, CHOCH)
        - Non-zero price if present
        """
        errors = []
        warnings = []
        
        sb_type = structure.get('type', None)
        price = structure.get('price', None)
        
        # Validate type
        if sb_type and sb_type not in ['MSS', 'BOS', 'CHOCH']:
            warnings.append(f"Unexpected structure type: {sb_type}")
        
        # Validate price if present
        if price is not None and price == 0:
            errors.append(f"Invalid structure price: {price}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            component_type="Structure Break",
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_component_list(
        components: List[Any],
        component_type: str,
        expected_tf: str,
        expected_bias: str = "BULLISH"
    ) -> Tuple[List[Any], int]:
        """
        Validate a list of components and return only valid ones
        
        Returns:
            (valid_components, rejected_count)
        """
        valid_components = []
        rejected_count = 0
        
        for component in components:
            # Select appropriate validator
            if component_type == "Order Block":
                result = ComponentTimeframeValidator.validate_order_block(
                    component, expected_tf, expected_bias
                )
            elif component_type == "FVG":
                result = ComponentTimeframeValidator.validate_fvg(
                    component, expected_tf, expected_bias
                )
            elif component_type == "Liquidity Zone":
                result = ComponentTimeframeValidator.validate_liquidity_zone(
                    component, expected_tf, expected_bias
                )
            elif component_type == "Liquidity Sweep":
                result = ComponentTimeframeValidator.validate_liquidity_sweep(
                    component, expected_tf, expected_bias
                )
            else:
                # Unknown type - log warning and include it
                logger.warning(f"Unknown component type: {component_type}")
                valid_components.append(component)
                continue
            
            # Log result
            result.log_result()
            
            # Add to valid list only if valid
            if result.is_valid:
                valid_components.append(component)
            else:
                rejected_count += 1
                logger.warning(f"🚫 Rejected {component_type} due to validation errors")
        
        return valid_components, rejected_count


class CrossTimeframeContaminationDetector:
    """
    Detects cross-timeframe contamination in signal generation
    Ensures components from different TFs don't mix inappropriately
    """
    
    @staticmethod
    def check_entry_scoring_contamination(
        components: Dict,
        signal_tf: str,
        structure_tf: str,
        htf_bias_tf: str
    ) -> List[str]:
        """
        Check for TF contamination in entry scoring
        
        Entry scoring should ONLY use signal_tf components
        """
        contamination_issues = []
        
        # Check Order Blocks
        obs = components.get('order_blocks', [])
        for ob in obs:
            ob_tf = getattr(ob, 'timeframe', None) or ob.get('timeframe', None)
            if ob_tf and ob_tf != signal_tf:
                contamination_issues.append(
                    f"Order Block from {ob_tf} used in entry (expected {signal_tf})"
                )
        
        # Check FVGs
        fvgs = components.get('fvgs', [])
        for fvg in fvgs:
            fvg_tf = getattr(fvg, 'timeframe', None) or fvg.get('timeframe', None)
            if fvg_tf and fvg_tf != signal_tf:
                contamination_issues.append(
                    f"FVG from {fvg_tf} used in entry (expected {signal_tf})"
                )
        
        return contamination_issues
    
    @staticmethod
    def log_contamination_check(
        contamination_issues: List[str],
        signal_tf: str
    ):
        """Log contamination check results"""
        if contamination_issues:
            logger.error("❌ CROSS-TF CONTAMINATION DETECTED:")
            for issue in contamination_issues:
                logger.error(f"   • {issue}")
        else:
            logger.info(f"✅ NO CONTAMINATION: All entry components from {signal_tf}")
