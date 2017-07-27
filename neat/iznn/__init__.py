"""
This module implements a spiking neural network.
Neurons are based on the model described by:

Izhikevich, E. M.
Simple Model of Spiking Neurons
IEEE TRANSACTIONS ON NEURAL NETWORKS, VOL. 14, NO. 6, NOVEMBER 2003

http://www.izhikevich.org/publications/spikes.pdf
"""

from neat.attributes import FloatAttribute
from neat.genes import BaseGene, DefaultConnectionGene
from neat.genome import DefaultGenomeConfig, DefaultGenome
from neat.graphs import required_for_output
from neat.six_util import itervalues

from neat.mypy_util import cast, NodeKey, GenomeKey, SpeciesKey, ConnKey, GeneKey, MYPY # pylint: disable=unused-import

if MYPY: # pragma: no cover
    from neat.mypy_util import Any, List, Tuple, Dict, Config # pylint: disable=unused-import

# a, b, c, d are the parameters of the Izhikevich model.
# a: the time scale of the recovery variable
# b: the sensitivity of the recovery variable
# c: the after-spike reset value of the membrane potential
# d: after-spike reset of the recovery variable
# The following parameter sets produce some known spiking behaviors:
# pylint: disable=bad-whitespace
REGULAR_SPIKING_PARAMS        = {'a': 0.02, 'b': 0.20, 'c': -65.0, 'd': 8.00} # type: Dict[str, float]
INTRINSICALLY_BURSTING_PARAMS = {'a': 0.02, 'b': 0.20, 'c': -55.0, 'd': 4.00} # type: Dict[str, float]
CHATTERING_PARAMS             = {'a': 0.02, 'b': 0.20, 'c': -50.0, 'd': 2.00} # type: Dict[str, float]
FAST_SPIKING_PARAMS           = {'a': 0.10, 'b': 0.20, 'c': -65.0, 'd': 2.00} # type: Dict[str, float]
THALAMO_CORTICAL_PARAMS       = {'a': 0.02, 'b': 0.25, 'c': -65.0, 'd': 0.05} # type: Dict[str, float]
RESONATOR_PARAMS              = {'a': 0.10, 'b': 0.25, 'c': -65.0, 'd': 2.00} # type: Dict[str, float]
LOW_THRESHOLD_SPIKING_PARAMS  = {'a': 0.02, 'b': 0.25, 'c': -65.0, 'd': 2.00} # type: Dict[str, float]


# TODO: Add mechanisms analogous to axon & dendrite propagation delay.


class IZNodeGene(BaseGene):
    """Contains attributes for the iznn node genes and determines genomic distances."""

    _gene_attributes = [FloatAttribute('bias'),
                        FloatAttribute('a'),
                        FloatAttribute('b'),
                        FloatAttribute('c'),
                        FloatAttribute('d')]

    def distance(self, other, config): # type: (IZNodeGene, DefaultGenomeConfig) -> float
        s = (abs(self.a - other.a) + abs(self.b - other.b) + # type: ignore
             abs(self.c - other.c) + abs(self.d - other.d)) # type: ignore
        return s * config.compatibility_weight_coefficient # type: ignore


class IZGenome(DefaultGenome):
    @classmethod
    def parse_config(cls, param_dict): # type: (Dict[str, Any]) -> DefaultGenomeConfig
        param_dict['node_gene_type'] = IZNodeGene
        param_dict['connection_gene_type'] = DefaultConnectionGene
        return DefaultGenomeConfig(param_dict)


class IZNeuron(object):
    """Sets up and simulates the iznn nodes (neurons)."""
    def __init__(self,
                 bias, # type: float
                 a, # type: float
                 b, # type: float
                 c, # type: float
                 d, # type: float
                 inputs # type: List[Tuple[NodeKey, float]]
                 ):
        # type: (...) -> None
        """
        a, b, c, d are the parameters of the Izhikevich model.

        :param float bias: The bias of the neuron.
        :param float a: The time-scale of the recovery variable.
        :param float b: The sensitivity of the recovery variable.
        :param float c: The after-spike reset value of the membrane potential.
        :param float d: The after-spike reset value of the recovery variable.
        :param inputs: A list of (input key, weight) pairs for incoming connections.
        :type inputs: list(tuple(int, float))
        """
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.bias = bias
        self.inputs = inputs

        # Membrane potential (millivolts).
        self.v = self.c # type: float

        # Membrane recovery variable.
        self.u = self.b * self.v # type: float

        self.fired = 0.0 # type: float
        self.current = self.bias # type: float

    def advance(self, dt_msec): # type: (float) -> None
        """
        Advances simulation time by the given time step in milliseconds.

        v' = 0.04 * v^2 + 5v + 140 - u + I
        u' = a * (b * v - u)

        if v >= 30 then
            v <- c, u <- u + d
        """
        # TODO: Make the time step adjustable, and choose an appropriate
        # numerical integration method to maintain stability.
        # TODO: The need to catch overflows indicates that the current method is
        # not stable for all possible network configurations and states.
        try:
            self.v += 0.5 * dt_msec * (0.04 * self.v ** 2 + 5 * self.v + 140 - self.u + self.current)
            self.v += 0.5 * dt_msec * (0.04 * self.v ** 2 + 5 * self.v + 140 - self.u + self.current)
            self.u += dt_msec * self.a * (self.b * self.v - self.u)
        except OverflowError:
            # Reset without producing a spike.
            self.v = self.c
            self.u = self.b * self.v

        self.fired = 0.0
        if self.v > 30.0:
            # Output spike and reset.
            self.fired = 1.0
            self.v = self.c
            self.u += self.d

    def reset(self): # type: () -> None
        """Resets all state variables."""
        self.v = self.c
        self.u = self.b * self.v
        self.fired = 0.0
        self.current = self.bias


class IZNN(object):
    """Basic IZNN network object."""
    def __init__(self,
                 neurons, # type: Dict[NodeKey, IZNeuron]
                 inputs, # type: List[NodeKey]
                 outputs # type: List[NodeKey]
                 ):
        # type: (...) -> None
        self.neurons = neurons
        self.inputs = inputs
        self.outputs = outputs
        self.input_values = {} # type: Dict[NodeKey, float]

    def set_inputs(self, inputs): # type: (List[float]) -> None
        """Assign input voltages."""
        assert len(inputs) == len(self.inputs)
        for i, v in zip(self.inputs, inputs):
            self.input_values[i] = v

    def reset(self): # type: () -> None
        """Reset all neurons to their default state."""
        for n in itervalues(self.neurons):
            n.reset()

    def get_time_step_msec(self): # type: () -> float
        # pylint: disable=no-self-use
        # TODO: Investigate performance or numerical stability issues that may
        # result from using this hard-coded time step.
        return 0.05

    def advance(self, dt_msec): # type: (float) -> List[float]
        for n in itervalues(self.neurons):
            n.current = n.bias
            for i, w in n.inputs:
                ineuron = self.neurons.get(i)
                if ineuron is not None:
                    ivalue = ineuron.fired
                else:
                    ivalue = self.input_values[i]

                n.current += ivalue * w

        for n in itervalues(self.neurons):
            n.advance(dt_msec)

        return [self.neurons[i].fired for i in self.outputs]

    @staticmethod
    def create(genome, config): # type: (IZGenome, Config) -> IZNN
        """ Receives a genome and returns its phenotype (a neural network). """
        genome_config = config.genome_config # type: DefaultGenomeConfig
        required = required_for_output(genome_config.input_keys, genome_config.output_keys, genome.connections)

        # Gather inputs and expressed connections.
        node_inputs = {} # type: Dict[NodeKey, List[Tuple[NodeKey, float]]]
        for cg in itervalues(genome.connections):
            if not cg.enabled:
                continue

            i, o = cast(ConnKey,cg.key) # type: NodeKey, NodeKey
            if o not in required and i not in required:
                continue

            if o not in node_inputs:
                node_inputs[o] = [(i, cg.weight)]
            else:
                node_inputs[o].append((i, cg.weight))

        neurons = {} # type: Dict[NodeKey, IZNeuron]
        for node_key in required:
            ng = cast(IZNodeGene,genome.nodes[node_key])
            inputs = node_inputs.get(node_key, []) # type: List[Tuple[NodeKey, float]]
            neurons[node_key] = IZNeuron(ng.bias, ng.a, ng.b, ng.c, ng.d, inputs) # type: ignore

        return IZNN(neurons, genome_config.input_keys, genome_config.output_keys)
