#!/usr/bin/env python3
"""
Dial Code Utilities - Shared parsing logic for EDC control prefixes.

This module provides shared functionality for parsing special dial code prefixes
that control EDC (Event Data Collection) packet behavior across multiple components.
"""

from typing import Optional, Tuple


def parse_special_dial_code(number: str) -> Tuple[str, bool, Optional[str]]:
    """
    Parse phone number for special EDC control codes.

    Codes:
    - *50<number>: Don't send EDC packet, just dial
    - *54<number>: Send EDC packet with "DC" code, then dial
    - *55<number>: Send EDC packet with normal code, then dial

    Args:
        number: Phone number potentially containing special prefix

    Returns:
        Tuple of (actual_number_to_dial, send_edc_packet, edc_code)
        - actual_number_to_dial: Number with prefix stripped
        - send_edc_packet: True if EDC packet should be sent
        - edc_code: EDC code to use ("DC" for *54, None for normal code)

    Examples:
        >>> parse_special_dial_code("*509723256826")
        ('9723256826', False, None)

        >>> parse_special_dial_code("*549723256826")
        ('9723256826', True, 'DC')

        >>> parse_special_dial_code("*559723256826")
        ('9723256826', True, None)

        >>> parse_special_dial_code("9723256826")
        ('9723256826', True, None)
    """
    if number.startswith("*50"):
        # *50: Don't send EDC packet
        return (number[3:], False, None)
    elif number.startswith("*54"):
        # *54: Send EDC packet with "DC" code
        return (number[3:], True, "DC")
    elif number.startswith("*55"):
        # *55: Send EDC packet with normal code
        return (number[3:], True, None)
    else:
        # No special code - default behavior (send EDC packet)
        return (number, True, None)
