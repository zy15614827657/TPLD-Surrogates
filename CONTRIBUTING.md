# 贡献指南

本项目以 `TSYGAI/TSYG-Surrogates` 为公司组织仓库，贡献者使用各自的个人 GitHub 账号提交。

## 提交方式

有仓库写入权限时，在公司仓库创建工作分支，提交修改并发起 Pull Request。由维护者按仓库规则审阅和合并。

没有写入权限时，可在仓库允许 Fork 的情况下将其 Fork 到个人账号，在个人 Fork 中提交，再向公司仓库发起 Pull Request。私有仓库的 Fork 能力取决于组织设置。

仓库归属由 GitHub 中的 owner 决定；个人作者身份由 Git 提交信息和 GitHub 关联邮箱决定。请使用关联到自己 GitHub 账号的邮箱，或该账号设置页面提供的准确 `noreply` 邮箱。只需为本仓库设置 Git 作者信息，无需改变其他项目。

## 新增研究案例

每个案例请同时提供：

1. 问题、输入与输出；明确真实场是否进入推理输入。
2. 模型检查点、验证/测试划分与评估范围。
3. 物理量、单位、色标、变形比例与时间含义。
4. 真实值、模型结果、误差对比及相应指标。
5. 可追溯的素材来源与生成方法。

展示素材放在 `assets/`，文档放在 `docs/`，指标摘要放在 `results/`。原始数据和模型权重由各研究项目单独管理。

提交前执行 `python scripts/verify_showcase.py` 检查链接、素材完整性、GIF 帧数及发布文件大小；更换素材后同步更新来源记录和相关文案。

## GitHub 参考

- [组织与个人账号协作](https://docs.github.com/en/organizations/collaborating-with-groups-in-organizations/about-organizations)
- [组织仓库角色与权限](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization)
- [设置提交邮箱](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address)
- [Fork 的权限与限制](https://docs.github.com/en/pull-requests/reference/forks)
