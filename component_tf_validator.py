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
        Validate Order Block component
        
        Checks:
        - Timeframe matches expected
        - Type matches bias (bullish OB for bullish bias)
        - Non-zero zone values
        - Correct high/low ordering (zone_high > zone_low)
        """
        errors = []
        warnings = []
        
        # Extract OB data (handle both dict and object)
        if hasattr(ob, '__dict__'):
            ob_type = getattr(ob, 'type', None)
            zone_low = getattr(ob, 'zone_low', None)
            zone_high = getattr(ob, 'zone_high', None)
            timeframe = getattr(ob, 'timeframe', None)
        else:
            ob_type = ob.get('type', None)
            zone_low = ob.get('zone_low', None)
            zone_high = ob.get('zone_high', None)
            timeframe = ob.get('timeframe', None)
        
        # Validate timeframe
        if timeframe != expected_tf:
            errors.append(f"TF mismatch: expected {expected_tf}, got {timeframe}")
        
        # Validate type matches bias
        if expected_bias.upper() == "BULLISH":
            if ob_type and "BEARISH" in ob_type.upper():
                errors.append(f"Bearish OB in bullish bias: {ob_type}")
        elif expected_bias.upper() == "BEARISH":
            if ob_type and "BULLISH" in ob_type.upper():
                errors.append(f"Bullish OB in bearish bias: {ob_type}")
        
        # Validate non-zero values
        if zone_low is None or zone_low == 0:
            errors.append(f"Invalid zone_low: {zone_low}")
        if zone_high is None or zone_high == 0:
            errors.append(f"Invalid zone_high: {zone_high}")
        
        # Validate correct ordering
        if zone_low and zone_high and zone_high <= zone_low:
            errors.append(f"Invalid ordering: zone_high ({zone_high}) <= zone_low ({zone_low})")
        
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
        Validate FVG (Fair Value Gap) component
        
        Checks:
        - Timeframe matches expected
        - is_bullish matches bias
        - Non-zero values
        - Correct top/bottom ordering (top > bottom)
        """
        errors = []
        warnings = []
        
        # Extract FVG data
        if hasattr(fvg, '__dict__'):
            is_bullish = getattr(fvg, 'is_bullish', None)
            bottom = getattr(fvg, 'bottom', None)
            top = getattr(fvg, 'top', None)
            timeframe = getattr(fvg, 'timeframe', None)
        else:
            is_bullish = fvg.get('is_bullish', None)
            bottom = fvg.get('bottom', None)
            top = fvg.get('top', None)
            timeframe = fvg.get('timeframe', None)
        
        # Validate timeframe
        if timeframe != expected_tf:
            errors.append(f"TF mismatch: expected {expected_tf}, got {timeframe}")
        
        # Validate type matches bias
        if expected_bias.upper() == "BULLISH" and is_bullish == False:
            errors.append(f"Bearish FVG in bullish bias")
        elif expected_bias.upper() == "BEARISH" and is_bullish == True:
            errors.append(f"Bullish FVG in bearish bias")
        
        # Validate non-zero values
        if bottom is None or bottom == 0:
            errors.append(f"Invalid bottom: {bottom}")
        if top is None or top == 0:
            errors.append(f"Invalid top: {top}")
        
        # Validate correct ordering
        if bottom and top and top <= bottom:
            errors.append(f"Invalid ordering: top ({top}) <= bottom ({bottom})")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            component_type="FVG",
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_liquidity_zone(
        lz: Any,
        expected_tf: str
    ) -> ValidationResult:
        """
        Validate Liquidity Zone component
        
        Checks:
        - Non-zero price
        - Valid type (BSL/SSL)
        """
        errors = []
        warnings = []
        
        # Extract data
        if hasattr(lz, '__dict__'):
            price = getattr(lz, 'price', None)
            lz_type = getattr(lz, 'type', None)
        else:
            price = lz.get('price', None)
            lz_type = lz.get('type', None)
        
        # Validate non-zero price
        if price is None or price == 0:
            errors.append(f"Invalid price: {price}")
        
        # Validate type
        if lz_type and lz_type not in ['BSL', 'SSL', 'EQL', 'EQH']:
            warnings.append(f"Unexpected liquidity type: {lz_type}")
        
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
        Validate Liquidity Sweep component
        
        Checks:
        - Sweep type matches bias direction
        - Non-zero price
        - Valid sweep type
        """
        errors = []
        warnings = []
        
        # Extract data
        if hasattr(sweep, '__dict__'):
            sweep_type = getattr(sweep, 'sweep_type', None)
            price = getattr(sweep, 'price', None)
        else:
            sweep_type = sweep.get('sweep_type', None)
            price = sweep.get('price', None)
        
        # Validate non-zero price
        if price is None or price == 0:
            errors.append(f"Invalid price: {price}")
        
        # Validate sweep type
        if sweep_type:
            if expected_bias.upper() == "BULLISH":
                # Bullish bias should sweep SSL (sell-side liquidity)
                if "BSL" in sweep_type.upper():
                    warnings.append(f"BSL sweep in bullish bias (unusual but possible)")
            elif expected_bias.upper() == "BEARISH":
                # Bearish bias should sweep BSL (buy-side liquidity)
                if "SSL" in sweep_type.upper():
                    warnings.append(f"SSL sweep in bearish bias (unusual but possible)")
        
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
                    component, expected_tf
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
