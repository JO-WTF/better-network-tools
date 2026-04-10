# Backend Server

```text
server/
├─ app.py                                  # 服务启动入口；初始化配置、依赖、WebSocket 服务并启动整个应用

├─ config/
│  ├─ settings.py                          # 全局配置定义与读取，比如 host、port、缓存目录、超时、并发数
│  └─ constants.py                         # 项目通用常量，比如默认语言、坐标精度、缓存批量落盘阈值、支持的 capability 名称

├─ transport/
│  └─ websocket/
│     ├─ server.py                         # WebSocket 服务创建与启动；负责 serve(handle_connection)
│     ├─ handler.py                        # WebSocket 消息总处理器；按 capability 分发请求到对应 service
│     ├─ request_parser.py                 # 解析并校验前端发来的 websocket 消息，转换成内部统一请求结构
│     ├─ response_builder.py               # 统一构造 progress / complete / error 等 websocket 返回消息
│     └─ connection_context.py             # 单个 websocket 连接上下文；保存连接级缓存、trace_id、用户本次配置等

├─ domain/
│  ├─ enums.py                             # 领域枚举定义，比如 provider 类型、capability 类型、输入模式、错误类型
│  ├─ errors.py                            # 领域异常定义，比如 ProviderNotSupportedError、InvalidCoordinateError
│  └─ models/
│     ├─ common.py                         # 通用数据模型；比如标准 success/fail 结果、请求元信息、分页或批处理信息
│     ├─ geocode.py                        # geocode 相关输入输出模型；如地址转坐标结果结构
│     ├─ reverse_geocode.py                # reverse geocode 相关模型；如坐标转地址结果结构
│     ├─ route.py                          # route 相关模型；如 distanceKm、durationMin、起终点坐标等
│     ├─ route_matrix.py                   # route matrix 相关模型；如二维距离矩阵、耗时矩阵结果结构
│     ├─ isochrone.py                      # isochrone 相关模型；如 polygon / feature collection 等结果结构
│     ├─ autocomplete.py                   # 搜索联想/地址补全相关模型；后续扩展 autocomplete 能力时使用
│     └─ map_match.py                      # 轨迹纠偏/地图匹配相关模型；后续扩展 map matching 时使用

├─ services/
│  ├─ provider_registry.py                 # 根据 config 识别 provider，并返回对应 provider 实例
│  ├─ capability_registry.py               # capability 注册表；维护 capability -> service 的映射关系
│  ├─ auth_service.py                      # 统一认证服务；负责获取 token / api key / auth header
│  ├─ cache_service.py                     # 统一缓存服务；屏蔽内存缓存与持久缓存细节
│  ├─ base_service.py                      # 通用 service 基类；封装 provider 选择、缓存、错误处理、结果标准化等共性流程
│  ├─ geocode_service.py                   # geocode 业务编排；接收 geocode 请求，调用 provider.geocode 并返回统一结果
│  ├─ reverse_geocode_service.py           # reverse geocode 业务编排；处理坐标转地址请求
│  ├─ route_service.py                     # route 业务编排；处理单起终点路径规划请求
│  ├─ route_matrix_service.py              # route matrix 业务编排；处理多起点多终点矩阵请求
│  ├─ isochrone_service.py                 # isochrone 业务编排；处理等时圈/等距圈请求
│  ├─ autocomplete_service.py              # autocomplete 业务编排；处理地址/POI 联想输入
│  └─ map_match_service.py                 # map matching 业务编排；处理轨迹纠偏请求

├─ providers/
│  ├─ base/
│  │  ├─ provider.py                       # Provider 基类/抽象接口；定义各 provider 统一能力入口
│  │  ├─ auth.py                           # 认证能力抽象；定义 get_auth() 等方法接口
│  │  ├─ geocode.py                        # geocode 能力抽象；定义 geocode() 方法签名
│  │  ├─ reverse_geocode.py                # reverse geocode 能力抽象；定义 reverse_geocode() 方法签名
│  │  ├─ route.py                          # route 能力抽象；定义 route() 方法签名
│  │  ├─ route_matrix.py                   # route matrix 能力抽象；定义 route_matrix() 方法签名
│  │  ├─ isochrone.py                      # isochrone 能力抽象；定义 isochrone() 方法签名
│  │  ├─ autocomplete.py                   # autocomplete 能力抽象；定义 autocomplete() 方法签名
│  │  └─ map_match.py                      # map matching 能力抽象；定义 map_match() 方法签名
│  │
│  ├─ common/
│  │  ├─ result_builder.py                 # provider 层通用结果构造工具；把第三方结果转成统一成功/失败结构
│  │  ├─ request_builder.py                # provider 层通用请求构造工具；封装 query/body/header 的公共处理
│  │  ├─ response_parser.py                # provider 层通用响应解析辅助；减少重复 JSON 取值代码
│  │  └─ errors.py                         # provider 层通用异常；如第三方接口失败、响应格式不匹配等
│  │
│  ├─ custom/
│  │  ├─ provider.py                       # custom provider 聚合入口；组合 token/geocode/route 等具体实现
│  │  ├─ token.py                          # custom provider 的 token 获取实现
│  │  ├─ geocode.py                        # custom provider 的 geocode 实现
│  │  ├─ reverse_geocode.py                # custom provider 的 reverse geocode 实现；未做可先占坑
│  │  ├─ route.py                          # custom provider 的 route 实现
│  │  ├─ route_matrix.py                   # custom provider 的 route matrix 实现；未做可先抛 NotImplementedError
│  │  ├─ isochrone.py                      # custom provider 的 isochrone 实现；未做可先抛 NotImplementedError
│  │  ├─ autocomplete.py                   # custom provider 的 autocomplete 实现；后续扩展
│  │  └─ map_match.py                      # custom provider 的 map matching 实现；后续扩展
│  │
│  ├─ mapbox/
│  │  ├─ provider.py                       # mapbox provider 聚合入口；组合 mapbox 各能力实现
│  │  ├─ token.py                          # mapbox 鉴权处理；如果只需要 api key，也可在这里统一返回
│  │  ├─ geocode.py                        # mapbox geocode 适配实现
│  │  ├─ reverse_geocode.py                # mapbox reverse geocode 适配实现
│  │  ├─ route.py                          # mapbox route 适配实现
│  │  ├─ route_matrix.py                   # mapbox route matrix 适配实现
│  │  ├─ isochrone.py                      # mapbox isochrone 适配实现
│  │  ├─ autocomplete.py                   # mapbox autocomplete 适配实现
│  │  └─ map_match.py                      # mapbox map matching 适配实现
│  │
│  └─ here/
│     ├─ provider.py                       # here provider 聚合入口；组合 here 各能力实现
│     ├─ token.py                          # here 鉴权处理；如果只用 apiKey，这里统一封装
│     ├─ geocode.py                        # here geocode 适配实现
│     ├─ reverse_geocode.py                # here reverse geocode 适配实现
│     ├─ route.py                          # here route 适配实现
│     ├─ route_matrix.py                   # here route matrix 适配实现
│     ├─ isochrone.py                      # here isochrone 适配实现
│     ├─ autocomplete.py                   # here autocomplete 适配实现
│     └─ map_match.py                      # here map matching 适配实现

├─ infrastructure/
│  ├─ http/
│  │  ├─ client.py                         # aiohttp 统一封装；统一 post/get、超时、ssl、异常处理、json 解析
│  │  ├─ retry.py                          # HTTP 重试策略；控制哪些错误可重试、重试次数、退避策略
│  │  └─ exceptions.py                     # HTTP 层异常定义；如 Timeout、BadJson、BadStatus 等
│  │
│  ├─ cache/
│  │  ├─ memory_cache.py                   # 进程内缓存/连接内缓存实现；保存本轮请求快速命中数据
│  │  ├─ persistent_cache.py               # 文件持久缓存实现；负责 load/set/flush/原子写入/并发锁保护
│  │  ├─ cache_manager.py                  # 缓存管理器；根据 provider+capability+config 选择正确缓存实例
│  │  └─ cache_key_builder.py              # 统一生成缓存 key；避免不同 capability 的 key 混淆
│  │
│  └─ logging/
│     ├─ logger.py                         # 日志初始化；统一日志格式、级别、输出位置
│     └─ access_log.py                     # 请求访问日志封装；记录 capability、provider、耗时、成功失败等

├─ utils/
│  ├─ coords.py                            # 坐标工具；坐标解析、经纬度格式化、精度处理、输入规范化
│  ├─ hash_utils.py                        # 哈希工具；用于缓存文件名、复杂请求 key 生成
│  ├─ json_utils.py                        # JSON 辅助工具；安全读取、序列化、容错解析
│  ├─ text_utils.py                        # 文本工具；地址字符串清洗、空白处理、大小写规范化
│  ├─ time_utils.py                        # 时间工具；耗时统计、时间戳、格式化
│  └─ batch_utils.py                       # 批处理工具；分片、限流、并发控制、批量任务辅助处理

├─ support_matrix.py                       # 显式声明每个 provider 支持哪些 capability；启动和运行时都可用
├─ dependency.py                           # 依赖组装入口；集中创建 provider_registry、services、cache_manager 等对象
└─ README.md                               # 项目说明；目录说明、已支持能力矩阵、消息协议、扩展新 provider 的步骤
```
