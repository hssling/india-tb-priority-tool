"""tbprio: the analysis of the TB priority tool (registered analysis plan, docs/analysis_plan.md).

Modules: panel (reading the long-format panel), shrink (empirical-Bayes priors, §6.1),
harm (benchmark and harm-averted draws, §6.2-§6.3), priority (P(top-k), tiers and the
small-but-far-behind flag, §6.4-§6.6), trend (the trend and the rising flag, §6.5, §7),
validate (H1-H3, labels and leave-one-out, §8), state (the State outputs, §6, §7, §10),
district (the district modules, §9), schema (the district input schema, §9.3), report (the
self-contained HTML reports, §10.2), table (CSV writing). The command line is __main__
(python -I -m tbprio state|district).
"""
