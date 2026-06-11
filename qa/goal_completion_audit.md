# `目标.txt` 逐项完成审计

审计日期：2026-06-11

本审计将 `目标.txt` 的要求逐项映射到当前工作区中的权威证据。这里的“完成”表示：
在本文明确声明的球面 BPP 快照、典型已调度用户、有效干扰耦合和方向性/正交 ISL
边界内，理论、代码、图、数据和中文结果解释已经闭环；它不表示已经完成真实星座外部验证，
也不把原论文复现误称为像素复制。

## 一、核心论文主线

核心论点已经固定为：

> 在固定总带宽和密集复用约束下，followers 的主要价值由无条件速率增益转变为可靠性
> 增益；其部署数量必须在端到端覆盖、平均与低尾速率、功率预算、复用、干扰隔离和 ISL
> 瓶颈之间联合权衡。

权威证据：

- `theory/resource_consistent_sinr_full_derivation_v1.tex`：摘要、研究问题、贡献、设计规则和结论。
- `theory/deployment_results_analysis.tex`：D1-D8 逐图解释与综合设计规则。
- `figures/deployment/figD2_optimal_follower_phase.*`：高可靠约束下的简约 follower 数量。
- `figures/deployment/figD3_power_consistency.*`：不同功率公平口径给出相反速率趋势。

## 二、模型层面要求

| `目标.txt` 要求 | 状态 | 权威证据 |
|---|---:|---|
| 完整系统模型图 | 完成 | 详细 TeX 内嵌 TikZ 系统模型图，包含服务/干扰 cluster、followers、可见区、RB 与 ISL |
| 固定总带宽数学约束 | 完成 | 详细 TeX 的资源模型、带宽单纯形与守恒证明；`src/sinr_model.py` |
| Cluster 内带宽分配策略 | 完成 | 均匀、leader 保底、覆盖约束网格优化；Fig.D1 |
| Cluster 间 frequency reuse | 完成 | `K` 的带宽代价、复用颜色和同频干扰模型；Fig.S5/D2 |
| `p_act` 物理定义 | 完成 | 详细 TeX 将其定义为典型 RB 条件同频重叠概率 |
| `G_I` 物理解释 | 完成 | 详细 TeX 将旁瓣、波束、极化、指向和调度隔离压缩为有效耦合 |
| Beam isolation 或 antenna pattern | 完成于有效耦合层 | 当前采用可扫描 beam-isolation 有效耦合；未声称具备真实天线方向图外部验证 |
| 固定 cluster 总功率 | 完成 | `power_model="fixed_cluster_total"`；Fig.D2/D3/D8 |
| Follower 装配/可用概率 | 完成 | `follower_availability_probability`；Fig.D7 |
| ISL 资源和干扰假设 | 完成 | 独立频段/高方向性、DF、半双工因子、ISL 门限；Fig.D7/D8 |
| 用户过程或 scheduled-user 假设 | 完成（方案 A） | 明确研究典型已调度用户，网络级指标标记为代理 |
| 可见边界修正 | 完成 | Parent 不可见但 follower 可见的积分与 Monte Carlo 修正 |
| 模型边界前置 | 完成 | 详细 TeX 第一部分独立列出假设与结论边界 |

## 三、理论层面要求

| `目标.txt` 要求 | 状态 | 权威证据 |
|---|---:|---|
| 服务 leader 距离/接触角分布 | 完成 | 最近 leader CDF/PDF、可见条件分布及证明 |
| 非服务 leader 条件分布 | 完成 | 条件球面 BPP 引理与证明 |
| Follower 球冠偏移与接触角 | 完成 | 球冠测度、偏移 PDF、方位积分表达 |
| Follower 自身可见性 | 完成 | 可见方位比例、边界 follower 引理 |
| 聚合干扰表达式 | 完成 | 正交 RB leader/follower 干扰向量 |
| Laplace transform | 完成 | 相关干扰向量条件联合 Laplace 变换定理与证明 |
| Moment matching | 完成 | 干扰均值/方差、Gamma 近似及完整几何验证 |
| Access coverage | 完成 | 正式定义、定理和事件推导 |
| End-to-end relay coverage | 完成 | LF 与 FU 联合成功事件、定理和证明 |
| Cluster rate | 完成 | 固定总带宽、DF 瓶颈与双工因子下的资源一致速率 |
| Network throughput | 完成于代理层 | `N_L E[R_cl]` 明确标记为典型已调度用户吞吐代理 |
| Spherical spectral efficiency | 完成于代理层 | 全球和可见区域归一化表达式及 CSV |
| Coverage-constrained optimization | 完成 | P1、P2、最优解存在性和统计稳健简约部署定义 |
| 最优/可行 follower 数量 | 完成于有限网格层 | Fig.D2；`N_F^\dagger` 明确限定为有限候选网格简约解 |
| 复杂度分析 | 完成 | 完整 MC、矩表、联合 LT 和部署搜索复杂度 |
| 退化情形验证 | 完成 | 无干扰、`N_F=0`、零可用率、独立/共享颜色、带宽守恒等测试 |

## 四、仿真层面要求

| `目标.txt` 要求 | 状态 | 权威证据 |
|---|---:|---|
| 原 noise-limited baseline | 完成 | 原论文 Fig.2-Fig.8 与 Fig.S1 |
| Full-reuse worst case | 完成 | Fig.I1-I5，保留为极端下界基准 |
| Orthogonal reuse-1 | 完成 | Fig.S1-S8 场景 |
| Coordinated case | 完成 | `K`、`p_act`、`G_I` 联合场景；Fig.S/D |
| Access 与 E2E coverage | 完成 | Fig.S2 及结果分析 |
| Rate vs `N_F` | 完成 | 原 Fig.6、Fig.S3、Fig.D3/D5 |
| Throughput vs `N_L` | 完成 | Fig.S4 与球面频谱效率代理 |
| Rate-reliability frontier | 完成 | Fig.S8 |
| `K` 敏感性 | 完成 | Fig.S5、Fig.D2 |
| `p_act` 敏感性 | 完成 | Fig.S5、Fig.D2 |
| `G_I` 敏感性 | 完成 | Fig.S5、Fig.D2 |
| Altitude 敏感性 | 完成 | 原 Fig.3/5、Fig.D4 |
| `theta_cap` 敏感性 | 完成 | Fig.D4 |
| `theta_max` 敏感性 | 完成 | Fig.D8 |
| Follower/leader transmit power | 完成 | 原 Fig.4/6/7 |
| Total cluster power | 完成 | Fig.D3/D8 |
| ISL threshold | 完成 | Fig.D8 |
| Ground threshold | 完成 | 原 Fig.2、Fig.S1/S6、Fig.D6 |
| Bandwidth split | 完成 | Fig.D1 |
| Beam coupling、traffic activity、reuse | 完成 | Fig.S5、Fig.D2 |
| `N_L` 与 `N_F` | 完成 | 原 Fig.8、Fig.S3/S4、Fig.D2 |
| Power consistency | 完成 | Fig.D3 |
| Optimal follower phase diagram | 完成于有限网格层 | Fig.D2 |
| Monte Carlo 置信区间 | 完成 | 主要 CSV 含均值 CI，D2 使用 Wilson 覆盖下界 |
| Rare-event 处理 | 完成 | 详细 TeX 给出零成功上界与解释规则 |
| Semi-analytical validation | 完成于边缘矩层 | Gamma moment match 与完整几何 MC 误差门禁 |

## 五、写作与交付要求

| `目标.txt` 要求 | 状态 | 权威证据 |
|---|---:|---|
| 中文详细 TeX 且推导不省略 | 完成 | `theory/resource_consistent_sinr_full_derivation_v1.tex/.pdf` |
| 中文结果分析、逐图解释与最终结论 | 完成 | `theory/deployment_results_analysis.tex/.pdf`，覆盖 D1-D8 |
| 明确贡献与相关工作 | 完成 | 详细 TeX 的定位章节与参考文献 |
| 与原 TWC 系统性对比 | 完成 | 详细 TeX 对比长表 |
| 符号统一、定理/证明/备注结构 | 完成 | 详细 TeX 的符号表及数学环境 |
| 设计规则 | 完成 | 详细 TeX 和结果分析中的部署规则 |
| 不过度声称与局限 | 完成 | BPP、标量耦合、scheduled user、代理指标和复现限制均显式披露 |
| 可运行代码、图和 CSV | 完成 | `src/`、`figures/`、对应 CSV 与 README 命令 |
| 自动 QA 与测试 | 完成 | `tests/`、`qa_sinr.py`、`qa_deployment.py`、稳定性审查 |

## 六、必须保留的结论边界

1. 原论文 Fig.2-Fig.8 是基于公开公式和欠明确参数进行的独立复现，不是像素复制；
   Fig.7 保留有记录的确定性校准，三类带宽采用有记录的 100 MHz 假设。
2. Fig.D2 的 `N_F^\dagger` 是公开有限 follower/带宽候选网格、预设协调场景和有限样本
   门禁下的统计稳健简约解，不是连续参数空间中的无条件全局最优。
3. 联合 Laplace 变换已经完整推导；大规模部署扫描使用边缘矩 Gamma 近似，并由最终完整
   几何共享颜色 Monte Carlo 审计。联合 LT 的直接高维数值求值不是当前图的计算主路径。
4. 真实星历、轨道时间相关性、切换、显式天线方向图、用户业务过程和完整调度器属于
   外部有效性扩展，不应把当前代理结果解释为真实运营网络绝对性能。

## 七、审计结论

`目标.txt` 中要求的论文主线、模型、逐步理论推导、结果图、参数敏感性、统计门禁、
中文结果分析、设计规则和结论边界均已有对应交付物。当前完成状态是：

> **在明确声明的研究边界内，目标级理论与数值研究交付完成；外部有效性扩展和原论文
> 像素级复现不被冒充为已完成。**
