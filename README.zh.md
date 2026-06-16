# DrunkAgent — 复现与批判性分析

对论文 **《DrunkAgent: Stealthy Memory Corruption in LLM-Powered Recommender
Agents》**（arXiv:2503.23804v3）的**从零复现**，目的是**压力测试论文的论断**，而不是复述它。

> 本任务的原始仓库是**空的**——没有任何代码。这是依据论文正文（Algorithm 1、
> Fig. 2、Table 4）对方法做的**独立重新实现**，写出来就是为了让核心论断能被真正运行。

## 哪些忠实于原文、哪些做了替换

论文的原始技术栈**在本沙箱里无法运行**：HuggingFace 和 OpenAI 都被网络封锁，没有
GPU，`torch`/`transformers` 也没装。因此：

| 组件 | 论文 | 本复现 | 原因 |
|---|---|---|---|
| 代理 / 受害者 LLM | Llama-3-8B-Instruct、gpt-4-turbo | 所有 LLM 角色统一用 **Claude (haiku-4.5)** | HF + OpenAI 被封、无 GPU |
| 贪心搜索打分（Eq. 4） | 白盒代理模型的 token 级 **NLL** | **黑盒代理 MRR**（目标项在探针用户上的倒数排名） | Claude 不暴露 logprob；MRR 直接优化攻击目标 |
| 数据集 | Amazon Review Data、Yelp | **合成 CD 数据集**（同样形态） | 数据在此无法下载 |
| Perplexity 指标（GPT-Neo） | GPT-Neo PPL | 用一个简单的**注入检测器**替代 | GPT-Neo 无法下载 |
| 规模 | ~99 用户，E=20，\|M_c\|=10 | ~20 用户，E=3，\|M_c\|=6 | API 预算 |

**忠实保留的部分：** 三种受害者设计（AgentCF/RAG/SEQ）及 Table 4 的提示模板；生成
模块（初始化 → 质量评估 → 特征整合/交叉 → 语言润色）；策略模块（Fig. 2 的五段
prompt-injection 组件）；HR@K / NDCG@K；Table 5 的消融结构；Table 6 的"灌醉成功率"指标。

由于后端和数据都不同，**绝对数值无法与论文直接对比**。能对比、也是本仓库目的所在的，
是那些**定性论断**：攻击是否真的打赢基线、哪个受害者最鲁棒、去掉策略模块攻击是否崩盘、
以及所谓"隐蔽"的文本是否真的隐蔽。

## 目录结构

```
repro/
  llm.py        Claude 客户端（OAuth bearer、磁盘缓存、重试）
  data.py       合成 CD 数据集（确定性，seed=2024）
  victims.py    AgentCF / AgentRAG / AgentSEQ + 排序解析器
  metrics.py    HR@K, NDCG@K
  attacks.py    基线 + DrunkAgent 生成（贪心搜索）+ 策略模块
  run.py        编排全流程 -> results/
results/        results.json + report.md（自动生成）
```

## 运行

```bash
N_USERS=20 python3 -m repro.run          # 完整复现
N_USERS=2 VICTIMS=AgentCF python3 -m repro.run   # 快速冒烟测试
```

生成的表格见 `results/report.md`；对论文的批判性解读（四个复现问题 + 优缺点）见
`ANALYSIS.md`（中文版 `ANALYSIS.zh.md`）。
