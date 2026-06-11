# Final Reviewer Audit

Date: 2026-06-11

## Current Status

The reproduction, resource-consistent SINR extension, and deployment study now
form a complete executable research package. The current automated review gates
pass, all 23 unit tests pass, Fig.2-Fig.8 trimmed aspect-ratio errors are below
5%, all SINR and deployment figures/CSV files exist, and the target-level
detailed derivation plus deployment results report compile twice without
unresolved references or layout warnings.

## Critical Findings Fixed During Review

1. Frequency reuse was previously modeled as interference thinning without the
   corresponding `1/K` bandwidth cost. The corrected rate model divides fixed
   ground spectrum by both `N_F+1` and the reuse factor.
2. Exact Monte Carlo previously resampled external cluster positions across
   follower resource blocks. The corrected exact path shares parent-leader
   geometry across leader and follower blocks.
3. Parent leaders outside the visibility boundary previously caused visible
   boundary followers to be omitted. Follower visibility is now evaluated
   independently.
4. Access coverage was previously easy to confuse with decode-and-forward
   end-to-end coverage. Both are now reported separately.
5. Custom leader-follower thresholds are now carried with simulation samples,
   so coverage-curve evaluation cannot silently fall back to `-5 dB`.
6. `N_L E[R_cl]` is now labeled a network-throughput proxy, not an exact
   network aggregate. The CSV also reports a spherical spectral-efficiency
   proxy.
7. Deployment optimization previously used a point-estimate coverage
   constraint. It now requires the Wilson 95% lower bound to exceed `0.99` in
   independent validation and a final exact-geometry shared-reuse-color audit.
8. Bandwidth allocation previously changed rate while leaving branch noise
   fixed. The deployment study now scales thermal noise with allocated
   bandwidth under the fixed-link-total-power convention.
9. The follower-count phase diagram now uses fixed cluster total ground-link
   power and reports the smallest design within 3% of the maximum feasible
   rate, avoiding unstable sample-maximum claims.
10. Independent validation previously rechecked only the selected candidate's
    coverage. It now reevaluates every scanned bandwidth-allocation candidate,
    reconstructs the feasible set and maximum rate, and reselects the 3%
    near-optimal parsimonious design from the validation sample.
11. The moment-matched deployment map previously omitted cross-resource-block
    interference correlation. Every final Fig.D2 point now passes an
    exact-geometry audit with shared cluster reuse color; candidates that fail
    this correlated gate are rejected in follower-count order.
12. Residual sensitivity gaps are now closed by Fig.D8, which separately scans
    maximum visible angle, fixed ground-link cluster total power, and the ISL
    decoding threshold.

## Verified Numerical Closure

- Gamma moment match versus shared-geometry exact Monte Carlo rate relative
  error: `1.56%`.
- Gamma moment match versus exact end-to-end coverage absolute error: `0.00275`.
- Semi-analytical versus Monte Carlo leader-coverage maximum absolute error in
  the independent gate: `0.0157`.
- Boundary-follower interference contribution at `N_L=900`: about `0.220%`.
- Primary Monte Carlo CSV outputs include 95% confidence intervals.
- All 50 selected deployment designs pass the `0.99` Wilson lower-bound
  constraint in independent-validation and exact correlated-audit samples.
- All 50 selected deployment designs remain within 3% of the feasible maximum
  rate recomputed from the independent-validation sample.
- Exact correlated-audit and independent-validation mean rates differ by at
  most `1.61%` across the 50 final Fig.D2 points.
- In five repeated-seed searches over the 25 Fig.D2 curve groups, 14 groups
  select one identical follower count in every repeat and 23 have at least 80%
  modal support. The one final point outside its marginal-model repeat range is
  explicitly explained by rejection of two smaller candidates in the exact
  correlated audit.
- Shared reuse color increases the measured leader/follower RB INR correlation
  from about `0.1693` to `0.3664`.
- Fixed per-satellite and fixed cluster-total power produce opposite rate
  trends, confirming that power accounting changes the deployment conclusion.
- Fig.D8 confirms that widening the visible region can reduce end-to-end
  coverage, all tested follower counts benefit from increased fixed cluster
  power, and stricter ISL thresholds never improve end-to-end coverage.

## Remaining Research Limitations

### Publication-Blocking External-Validity Work

- The model uses spherical BPP snapshot geometry rather than orbital dynamics or
  a real constellation ephemeris.
- Interference isolation is represented by a scalar coupling gain instead of an
  explicit antenna pattern, pointing error, polarization, and beam schedule.
- No user point process, traffic-arrival process, queueing model, or optimized
  scheduler is defined. Network-level metrics are therefore comparison proxies.
- Fig.D2 is a statistically robust parsimonious choice on a documented finite
  follower/bandwidth grid and preset coordination scenarios. It is not a
  continuous-space global optimum or a joint numerical solution of all P1/P2
  variables.
- The detailed derivation now contains a literature-grounded related-work and
  novelty-positioning section; a submission manuscript would still need the
  target journal's final citation style and a broader literature refresh.

### Reproduction Limits

- Fig.2-Fig.8 are independent equation-based reproductions, not pixel copies.
  Their aspect ratios now match closely, but fonts, rendering, and some curves
  still differ at pixel level.
- Fig.7 remains a documented deterministic calibration because the source paper
  does not disclose the full power-allocation optimization procedure.
- The paper does not list the three bandwidths; the reproduction continues to
  use the documented `100 MHz` assumption.

## Reviewer Verdict

The project passes internal mathematical, numerical, artifact, and
reproducibility checks. It is suitable as a rigorous research prototype and as
the basis for a manuscript. It should not yet claim real-constellation
performance or exact pixel-level reproduction. The highest-value next study is
to replace BPP/scalar coupling with ephemeris-driven geometry and explicit beam
patterns, then re-evaluate the rate-reliability frontier.
