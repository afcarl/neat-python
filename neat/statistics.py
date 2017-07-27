"""
Gathers (via the reporting interface) and provides (to callers and/or a file)
the most-fit genomes and information on genome/species fitness and species sizes.
"""
import copy
import csv

from neat.math_util import mean, stdev, median2
from neat.reporting import BaseReporter
from neat.six_util import iteritems

from neat.mypy_util import * # pylint: disable=unused-wildcard-import

if MYPY: # pragma: no cover
    from neat.mypy_util import Callable, Config # pylint: disable=unused-import
    from neat.species import DefaultSpeciesSet # pylint: disable=unused-import


# TODO: Make a version of this reporter that doesn't continually increase memory usage.
# (Maybe periodically write blocks of history to disk, or log stats in a database?)

class StatisticsReporter(BaseReporter):
    """
    Gathers (via the reporting interface) and provides (to callers and/or a file)
    the most-fit genomes and information on genome/species fitness and species sizes.
    """
    def __init__(self):
        BaseReporter.__init__(self)
        self.most_fit_genomes = [] # type: List[KnownGenome] # XXX
        self.generation_statistics = [] # type: List[Dict[SpeciesKey, Dict[GenomeKey, float]]]
        #self.generation_cross_validation_statistics = []

    def post_evaluate(self,
                      config, # type: Config
                      population, # type: Dict[GenomeKey, KnownGenome] # XXX
                      species, # type: DefaultSpeciesSet # XXX
                      best_genome # type: KnownGenome # XXX
                      ):
        # type: (...) -> None
        self.most_fit_genomes.append(copy.deepcopy(best_genome))

        # Store the fitnesses of the members of each currently active species.
        species_stats = {} # type: Dict[SpeciesKey, Dict[GenomeKey, float]]
        #species_cross_validation_stats = {}
        for sid, s in iteritems(species.species):
            species_stats[sid] = dict((k, v.fitness) for k, v in iteritems(s.members))
            ##species_cross_validation_stats[sid] = dict((k, v.cross_fitness) for
##                                                       k, v in iteritems(s.members))
        self.generation_statistics.append(species_stats)
        #self.generation_cross_validation_statistics.append(species_cross_validation_stats)

    def get_fitness_stat(self,
                         f # type: Callable[[Iterable[float]], Union[Sequence[float], float]]
                         ):
        # type: (...) -> List[Union[Sequence[float], float]]
        stat = [] # type: List[Union[Sequence[float], float]]
        for stats in self.generation_statistics:
            scores = [] # type: List[float]
            for species_stats in stats.values():
                scores.extend(species_stats.values())
            stat.append(f(scores))

        return stat

    def get_fitness_mean(self): # type: () -> List[float]
        """Get the per-generation mean fitness."""
        return self.get_fitness_stat(mean) # type: ignore

    def get_fitness_stdev(self): # type: () -> List[float]
        """Get the per-generation standard deviation of the fitness."""
        return self.get_fitness_stat(stdev) # type: ignore

    def get_fitness_median(self): # type () -> List[float]
        """Get the per-generation median fitness."""
        return self.get_fitness_stat(median2)

    def get_average_cross_validation_fitness(self): # pragma: no cover
        """Get the per-generation average cross_validation fitness."""
        avg_cross_validation_fitness = []
        for stats in self.generation_cross_validation_statistics:
            scores = [] # type: List[float]
            for fitness in stats.values():
                scores.extend(fitness)
            avg_cross_validation_fitness.append(mean(scores))

        return avg_cross_validation_fitness

    def best_unique_genomes(self, n): # type: (int) -> List[KnownGenome] # XXX
        """Returns the most n fit genomes, with no duplication."""
        best_unique = {} # type: Dict[GenomeKey, KnownGenome] # XXX
        for g in self.most_fit_genomes:
            best_unique[g.key] = g
        best_unique_list = list(best_unique.values())

        def key(genome): # type: (KnownGenome) -> float # XXX
            return genome.fitness

        return sorted(best_unique_list, key=key, reverse=True)[:n]

    def best_genomes(self, n): # type: (int) -> List[KnownGenome] # XXX
        """Returns the n most fit genomes ever seen."""
        def key(g): # type: (KnownGenome) -> float # XXX
            return g.fitness

        return sorted(self.most_fit_genomes, key=key, reverse=True)[:n]

    def best_genome(self): # type: () -> KnownGenome # XXX
        """Returns the most fit genome ever seen."""
        return self.best_genomes(1)[0]

    def save(self): # type: () -> None
        self.save_genome_fitness()
        self.save_species_count()
        self.save_species_fitness()

    def save_genome_fitness(self,
                            delimiter=' ', # type: str
                            filename='fitness_history.csv', # type: str
                            with_cross_validation=False # type: bool
                            ):
        # type: (...) -> None
        """ Saves the population's best and average fitness. """
        with open(filename, 'w') as f:
            w = csv.writer(f, delimiter=delimiter)

            best_fitness = [c.fitness for c in self.most_fit_genomes]
            avg_fitness = self.get_fitness_mean()

            if with_cross_validation: # pragma: no cover
                pass
##                cv_best_fitness = [c.cross_fitness for c in self.most_fit_genomes]
##                cv_avg_fitness = self.get_average_cross_validation_fitness()
##                for best, avg, cv_best, cv_avg in zip(best_fitness,
##                                                      avg_fitness,
##                                                      cv_best_fitness,
##                                                      cv_avg_fitness):
##                    w.writerow([best, avg, cv_best, cv_avg])
            else:
                for best, avg in zip(best_fitness, avg_fitness):
                    w.writerow([best, avg])

    def save_species_count(self,
                           delimiter=' ', # type: str
                           filename='speciation.csv' # type: str
                           ):
        # type: (...) -> None
        """ Log speciation throughout evolution. """
        with open(filename, 'w') as f:
            w = csv.writer(f, delimiter=delimiter)
            for s in self.get_species_sizes():
                w.writerow(s)

    def save_species_fitness(self,
                             delimiter=' ', # type: str
                             null_value='NA', # type: str
                             filename='species_fitness.csv' # type: str
                             ):
        # type: (...) -> None
        """ Log species' average fitness throughout evolution. """
        with open(filename, 'w') as f:
            w = csv.writer(f, delimiter=delimiter)
            for s in self.get_species_fitness(null_value):
                w.writerow(s)

    def get_species_sizes(self): # type: () -> List[List[int]]
        all_species = set() # type: Set[SpeciesKey]
        for gen_data in self.generation_statistics:
            all_species = all_species.union(gen_data.keys())

        max_species = max(all_species)
        species_counts = [] # type: List[List[int]]
        for gen_data in self.generation_statistics:
            species = [len(gen_data.get(cast(SpeciesKey,sid), [])) for sid in range(1, max_species + 1)]
            species_counts.append(species)

        return species_counts

    def get_species_fitness(self,
                            null_value='' # type: str
                            ):
        # type: (...) -> List[List[Union[float, str]]]
        all_species = set() # type: Set[SpeciesKey]
        for gen_data in self.generation_statistics:
            all_species = all_species.union(gen_data.keys())

        max_species = max(all_species)
        species_fitness = [] # type: List[List[Union[float, str]]]
        for gen_data in self.generation_statistics:
            member_fitness = [gen_data.get(cast(SpeciesKey,sid), []) for sid in range(1, max_species + 1)]
            fitness = [] # type: List[Union[float, str]]
            for mf in member_fitness:
                if mf:
                    fitness.append(mean(mf))
                else:
                    fitness.append(null_value)
            species_fitness.append(fitness)

        return species_fitness


