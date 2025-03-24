# 讯飞 ASR 工具 Docker 部署指南

本文档提供了如何使用 Docker 在生产环境中部署讯飞 ASR 工具的详细说明。

## 部署架构

该 Docker 部署采用了以下安全实践：

- 使用多阶段构建减小镜像大小
- 使用非 root 用户运行应用
- 设置资源限制防止资源耗尽
- 配置健康检查确保服务可用性
- 使用 volume 挂载持久化上传文件

## 前置条件

- Docker 19.03 或更高版本
- Docker Compose 1.27 或更高版本
- 讯飞开放平台的 AppID 和 SecretKey

## 部署步骤

### 1. 构建并启动服务

```bash
# 在项目根目录下执行
docker-compose up -d
```

服务将在后台启动，并监听 18080 端口。

### 2. 查看日志

```bash
docker-compose logs -f
```

### 3. 停止服务

```bash
docker-compose down
```

## API 使用说明

服务启动后，可以通过以下端点访问 API：

- 健康检查: `GET http://your-server-ip:18080/`
- 文件上传: `POST http://your-server-ip:18080/upload/file`
- URL 上传: `POST http://your-server-ip:18080/upload/url`
- 直接 URL 上传: `POST http://your-server-ip:18080/upload/direct_url`
- 获取结果: `GET http://your-server-ip:18080/result/{task_id}`

## 安全注意事项

1. **API 凭证保护**：不要在代码中硬编码 AppID 和 SecretKey，建议通过环境变量或安全的配置管理系统提供
2. **网络安全**：在生产环境中，建议在 Docker 前配置反向代理（如 Nginx）并启用 HTTPS
3. **资源限制**：docker-compose.yml 中已配置资源限制，可根据实际需求调整
4. **日志轮转**：已配置日志大小限制和轮转策略，防止磁盘被日志填满
5. **定期更新**：定期更新基础镜像和依赖，修复潜在安全漏洞

## 监控与维护

- 使用 `docker-compose ps` 检查容器状态
- 使用 `docker stats` 监控容器资源使用情况
- 定期备份 uploads 目录中的重要数据

## 故障排除

1. 如果服务无法启动，检查日志中的错误信息
2. 确保 8080 端口未被其他服务占用
3. 验证 uploads 目录权限是否正确
4. 检查网络连接是否可以访问讯飞 API
