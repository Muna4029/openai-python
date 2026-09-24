from __future__ import annotations

import re
import inspect
from typing import Any, List, Union, Callable, Sequence, get_args, get_origin


def function_has_argument(func: Callable[..., Any], arg_name: str) -> bool:
    """Returns whether or not the given function has a specific parameter"""
    sig = inspect.signature(func)
    return arg_name in sig.parameters


def _normalize_type_str(type_str: str) -> str:
    """Normalize type string for comparison by treating SequenceNotStr as List."""
    # Replace SequenceNotStr with List
    type_str = re.sub(r'SequenceNotStr\[', r'List[', type_str)
    return type_str


def _types_are_compatible(type1: Any, type2: Any) -> bool:
    """Check if two types are compatible, handling special cases like SequenceNotStr vs List."""
    # Direct equality check
    if type1 == type2:
        return True

    # If annotations are strings (due to PEP 563 / `from __future__ import annotations`)
    if isinstance(type1, str) and isinstance(type2, str):
        # Normalize both strings and compare
        normalized1 = _normalize_type_str(type1)
        normalized2 = _normalize_type_str(type2)
        return normalized1 == normalized2

    # Try to get origins and args for non-string annotations
    try:
        origin1, args1 = get_origin(type1), get_args(type1)
        origin2, args2 = get_origin(type2), get_args(type2)
    except TypeError:
        # If we can't get origin/args, fall back to string comparison
        if isinstance(type1, str) and isinstance(type2, str):
            return _normalize_type_str(type1) == _normalize_type_str(type2)
        return type1 == type2

    # If both are Union types, check if their args are compatible
    if origin1 is Union and origin2 is Union:
        args1_set = set(args1)
        args2_set = set(args2)

        # Normalize Sequence to List
        normalized_args1 = set()
        normalized_args2 = set()

        for arg in args1_set:
            if get_origin(arg) is Sequence:
                normalized_args1.add(List[get_args(arg)[0]] if get_args(arg) else List)
            else:
                normalized_args1.add(arg)

        for arg in args2_set:
            if get_origin(arg) is Sequence:
                normalized_args2.add(List[get_args(arg)[0]] if get_args(arg) else List)
            else:
                normalized_args2.add(arg)

        return normalized_args1 == normalized_args2

    return False


def assert_signatures_in_sync(
    source_func: Callable[..., Any],
    check_func: Callable[..., Any],
    *,
    exclude_params: set[str] = set(),
    description: str = "",
) -> None:
    """Ensure that the signature of the second function matches the first."""

    check_sig = inspect.signature(check_func)
    source_sig = inspect.signature(source_func)

    errors: list[str] = []

    for name, source_param in source_sig.parameters.items():
        if name in exclude_params:
            continue

        custom_param = check_sig.parameters.get(name)
        if not custom_param:
            errors.append(f"the `{name}` param is missing")
            continue

        if not _types_are_compatible(source_param.annotation, custom_param.annotation):
            errors.append(
                f"types for the `{name}` param do not match; source={repr(source_param.annotation)} checking={repr(custom_param.annotation)}"
            )
            continue

    if errors:
        raise AssertionError(
            f"{len(errors)} errors encountered when comparing signatures{description}:\n\n" + "\n\n".join(errors)
        )
