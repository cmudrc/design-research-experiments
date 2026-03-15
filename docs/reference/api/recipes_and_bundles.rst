Recipes and Bundles
===================

Use this part of the API when you want a strong starting point instead of
authoring every study object by hand. Recipe builders encode recurring study
shapes, while bundles provide reusable agent/problem defaults that those recipe
builders can attach to a study.

The design intent is that you should be able to start from a sensible default,
override only the parts that matter for your question, and still end up with a
fully typed :class:`design_research_experiments.Study`.

.. currentmodule:: design_research_experiments

Recipe Override Objects
-----------------------

These configuration objects let you replace selected sections of a recipe-built
study without rewriting the recipe from scratch. Any field left as ``None``
keeps the recipe default for that section.

.. autosummary::
   :nosignatures:

   RecipeStudyConfig
   PromptFramingConfig
   OptimizationBenchmarkConfig
   AgentArchitectureComparisonConfig
   GrammarScaffoldConfig
   HumanVsAgentProcessConfig
   DiversityAndExplorationConfig

.. autoclass:: RecipeStudyConfig

.. autoclass:: PromptFramingConfig

.. autoclass:: OptimizationBenchmarkConfig

.. autoclass:: AgentArchitectureComparisonConfig

.. autoclass:: GrammarScaffoldConfig

.. autoclass:: HumanVsAgentProcessConfig

.. autoclass:: DiversityAndExplorationConfig

Benchmark Bundles
-----------------

Bundles package default problem IDs, agent specs, and metadata for recurring
benchmark families. They are useful when you want a repeatable baseline without
copying integration payloads into every study definition.

.. autosummary::
   :nosignatures:

   BenchmarkBundle
   ideation_bundle
   optimization_bundle
   grammar_problem_bundle
   human_vs_agent_bundle

.. autoclass:: BenchmarkBundle

.. autofunction:: ideation_bundle

.. autofunction:: optimization_bundle

.. autofunction:: grammar_problem_bundle

.. autofunction:: human_vs_agent_bundle

Recipe Builders
---------------

These helpers return complete study definitions for common design-research
scenarios. Use them when you want a working starting point and plan to tune the
question through override objects rather than reassemble the whole study model.

.. autosummary::
   :nosignatures:

   build_prompt_framing_study
   build_optimization_benchmark_study
   build_agent_architecture_comparison_study
   build_grammar_scaffold_study
   build_human_vs_agent_process_study
   build_diversity_and_exploration_study

.. autofunction:: build_prompt_framing_study

.. autofunction:: build_optimization_benchmark_study

.. autofunction:: build_agent_architecture_comparison_study

.. autofunction:: build_grammar_scaffold_study

.. autofunction:: build_human_vs_agent_process_study

.. autofunction:: build_diversity_and_exploration_study
