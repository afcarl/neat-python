"""Utilities for working with mypy for type checking."""

MYPY = False # pragma: no cover

__all__ = ['cast', 'NodeKey', 'GenomeKey', 'SpeciesKey', 'ConnKey', 'MYPY'] # pragma: no cover

if MYPY: # pragma: no cover
    from typing import (Iterable, Set, List, Sequence, NewType, # pylint: disable=unused-import
                        Tuple, Optional, Union, cast, Dict, Any, TextIO)
    from neat.config import DefaultClassConfig, Config # pylint: disable=unused-import
    from neat.genome import DefaultGenomeConfig, DefaultGenome # pylint: disable=unused-import
    from neat.iznn import IZGenome # pylint: disable=unused-import
    KnownConfig = Union[DefaultClassConfig, Config, DefaultGenomeConfig] # XXX
    KnownGenome = Union[DefaultGenome, IZGenome]
    NodeKey = NewType('NodeKey', int)
    ConnKey = Tuple[NodeKey, NodeKey]
    GeneKey = Union[NodeKey, ConnKey]
    GenomeKey = NewType('GenomeKey', int) # c_type: c_uint
    SpeciesKey = NewType('SpeciesKey', int) # c_type: c_uint
    __all__ += ['Iterable', 'Set', 'List', 'Sequence', # not NewType
                'Tuple', 'Optional', 'Union', 'Dict', 'Any', 'TextIO',
                'ConnKey', 'GeneKey', 'KnownConfig', 'KnownGenome']
else:
    NodeKey = None # pylint: disable=invalid-name
    GenomeKey = None # pylint: disable=invalid-name
    SpeciesKey = None # pylint: disable=invalid-name
    ConnKey = None # pylint: disable=invalid-name

    def cast(ignored_type, var):
        return var
