#!/usr/bin/env python3
"""
skill_architecture - 架构设计辅助脚本
系统性设计软件架构和技术方案
"""

import argparse
import json
import sys
from typing import Dict, Any, List, Optional


# 架构模式库
ARCHITECTURE_PATTERNS = {
    "layered": {
        "name": "分层架构",
        "适用": "传统Web应用、业务逻辑清晰",
        "组件": ["表现层", "业务逻辑层", "数据访问层"],
        "优点": "简单清晰、易于理解",
        "缺点": "耦合度高、扩展性受限"
    },
    "microservice": {
        "name": "微服务架构",
        "适用": "大规模系统、需要独立扩展",
        "组件": ["API Gateway", "服务集群", "服务注册中心", "配置中心", "消息队列"],
        "优点": "独立部署、技术异构",
        "缺点": "复杂度高、运维成本高"
    },
    "event_driven": {
        "name": "事件驱动架构",
        "适用": "实时系统、异步处理",
        "组件": ["事件总线", "事件处理器", "事件存储"],
        "优点": "解耦、扩展性强",
        "缺点": "调试困难、事务复杂"
    },
    "cqrs": {
        "name": "CQRS架构",
        "适用": "复杂业务、读写分离",
        "组件": ["命令处理器", "查询处理器", "事件溯源"],
        "优点": "读写优化、灵活扩展",
        "缺点": "复杂度高、数据一致性挑战"
    },
    "ddd": {
        "name": "DDD领域驱动设计",
        "适用": "复杂业务领域",
        "组件": ["聚合根", "领域事件", "限界上下文", "防腐层"],
        "优点": "业务对齐、易于演进",
        "缺点": "学习成本高"
    }
}

# 技术栈推荐
TECH_STACKS = {
    "web_app": {
        "frontend": ["React", "Vue.js", "Angular"],
        "backend": ["Spring Boot", "Django", "Express", "FastAPI"],
        "database": ["PostgreSQL", "MySQL"],
        "cache": ["Redis"],
        "gateway": ["Nginx", "Kong"]
    },
    "ecommerce": {
        "frontend": ["React/Vue", "Next.js/Nuxt"],
        "backend": ["Spring Cloud", "Django", "Go"],
        "database": ["PostgreSQL", "MongoDB"],
        "cache": ["Redis", "Memcached"],
        "queue": ["RabbitMQ", "Kafka"],
        "search": ["Elasticsearch"]
    },
    "realtime": {
        "websocket": ["Socket.IO", "SockJS"],
        "message_queue": ["Kafka", "RabbitMQ"],
        "stream_processing": ["Flink", "Spark Streaming"]
    },
    "mobile": {
        "frontend": ["Flutter", "React Native"],
        "backend": ["Spring Boot", "Go"],
        "database": ["PostgreSQL", "MongoDB"],
        "push": ["Firebase", "极光推送"]
    }
}


def analyze_requirements(requirements: str, scale: str) -> Dict[str, Any]:
    """分析需求，提取关键信息"""
    
    req_lower = requirements.lower()
    
    # 检测关键词
    keywords = {
        "realtime": ["实时", "聊天", "推送", "websocket", "直播", "监控"],
        "ecommerce": ["电商", "购物", "订单", "支付", "商品", "秒杀"],
        "social": ["社交", "社区", "评论", "点赞", "关注"],
        "data_intensive": ["大数据", "分析", "报表", "BI", "数据挖掘"],
        "iot": ["物联网", "设备", "传感器", "边缘计算"],
        "ai": ["AI", "机器学习", "推荐", " NLP", "图像识别"]
    }
    
    detected = []
    for category, kws in keywords.items():
        if any(k in req_lower for k in kws):
            detected.append(category)
    
    # 检测性能要求
    perf_keywords = ["高并发", "万级", "百万", "QPS", "TPS", "低延迟", "高性能"]
    has_perf = any(k in req_lower for k in perf_keywords)
    
    return {
        "detected_categories": detected,
        "has_performance_requirement": has_perf,
        "scale": scale or "medium"
    }


def suggest_architecture(requirements: str, scale: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
    """生成架构建议"""
    
    analysis = analyze_requirements(requirements, scale)
    
    # 选择架构模式
    if analysis["has_performance_requirement"] or scale == "large":
        pattern = "microservice"
    elif "realtime" in analysis["detected_categories"]:
        pattern = "event_driven"
    elif any(c in ["ecommerce", "social"] for c in analysis["detected_categories"]):
        pattern = "layered"  # 可演进为微服务
    else:
        pattern = "layered"
    
    pattern_info = ARCHITECTURE_PATTERNS[pattern]
    
    # 选择技术栈
    categories = analysis["detected_categories"]
    if "ecommerce" in categories:
        tech_stack = TECH_STACKS["ecommerce"]
    elif "realtime" in categories:
        tech_stack = TECH_STACKS["realtime"]
    elif "ai" in categories:
        tech_stack = {"ml": ["PyTorch", "TensorFlow"], "data": ["Spark", "Flink"]}
    else:
        tech_stack = TECH_STACKS["web_app"]
    
    # 生成组件
    components = []
    if pattern == "layered":
        components = [
            {"name": "frontend", "responsibility": "用户界面展示", "tech": tech_stack.get("frontend", ["React"])[0]},
            {"name": "backend-api", "responsibility": "业务逻辑处理", "tech": tech_stack.get("backend", ["Spring Boot"])[0]},
            {"name": "database", "responsibility": "数据持久化", "tech": tech_stack.get("database", ["PostgreSQL"])[0]},
        ]
    elif pattern == "microservice":
        components = [
            {"name": "api-gateway", "responsibility": "请求路由/认证", "tech": "Kong/Nginx"},
            {"name": "service-registry", "responsibility": "服务注册发现", "tech": "Nacos/Consul"},
            {"name": "user-service", "responsibility": "用户管理", "tech": "Spring Boot/Go"},
            {"name": "order-service", "responsibility": "订单处理", "tech": "Spring Boot/Go"},
            {"name": "message-queue", "responsibility": "异步消息", "tech": "RabbitMQ/Kafka"},
            {"name": "cache-layer", "responsibility": "缓存加速", "tech": "Redis"},
            {"name": "config-center", "responsibility": "配置管理", "tech": "Apollo/Nacos"},
        ]
    
    # 生成架构图 (Mermaid格式)
    diagram = generate_diagram(pattern, components)
    
    # 权衡分析
    tradeoffs = [
        {
            "decision": f"选择{pattern_info['name']}",
            "pros": pattern_info["优点"],
            "cons": pattern_info["缺点"]
        }
    ]
    
    # 扩展性考虑
    extensibility = []
    if scale in ["large", "enterprise"]:
        extensibility.append("预留数据库分片空间")
        extensibility.append("服务支持水平扩展")
        extensibility.append("缓存层支持扩展")
    
    return {
        "architecture_pattern": pattern,
        "pattern_name": pattern_info["name"],
        "architecture_diagram": diagram,
        "components": components,
        "technology_stack": tech_stack,
        "tradeoffs": tradeoffs,
        "extensibility": extensibility,
        "analysis": analysis
    }


def generate_diagram(pattern: str, components: List[Dict]) -> str:
    """生成 Mermaid 架构图"""
    
    if pattern == "layered":
        diagram = """```mermaid
graph TD
    subgraph 前端层
        FE[用户界面]
    end
    
    subgraph 后端层
        API[API服务]
        BL[业务逻辑]
    end
    
    subgraph 数据层
        DB[(数据库)]
        Cache[(缓存)]
    end
    
    FE --> API
    API --> BL
    BL --> DB
    BL --> Cache
```"""
    elif pattern == "microservice":
        diagram = """```mermaid
graph TB
    subgraph 网关层
        GW[API Gateway]
    end
    
    subgraph 服务层
        US[用户服务]
        OS[订单服务]
        PS[商品服务]
    end
    
    subgraph 支撑层
        MQ[消息队列]
        SC[配置中心]
        SR[服务注册]
        Cache[(缓存)]
    end
    
    subgraph 数据层
        DB[(主库)]
        DR[(只读库)]
    end
    
    GW --> US
    GW --> OS
    GW --> PS
    
    US --> Cache
    OS --> MQ
    PS --> DB
    
    US --> SR
    OS --> SR
    PS --> SR
    
    OS --> DB
    OS --> DR
```"""
    else:
        diagram = """```mermaid
graph LR
    A[客户端] --> B[服务]
    B --> C[(数据库)]
```"""
    
    return diagram


def generate_adr(architecture: Dict[str, Any]) -> List[Dict[str, str]]:
    """生成架构决策记录"""
    
    adrs = [
        {
            "title": f"采用{architecture['pattern_name']}",
            "status": "Accepted",
            "context": "基于需求分析和规模评估",
            "decision": f"选择{architecture['pattern_name']}作为系统架构",
            "consequences": f"优点: {architecture['tradeoffs'][0]['pros']} / 缺点: {architecture['tradeoffs'][0]['cons']}"
        }
    ]
    
    return adrs


def main():
    parser = argparse.ArgumentParser(description='架构设计辅助工具')
    parser.add_argument('--requirements', type=str, required=True, help='业务需求描述')
    parser.add_argument('--scale', type=str, default='medium', 
                        choices=['small', 'medium', 'large', 'enterprise'],
                        help='系统规模')
    parser.add_argument('--constraints', type=str, default='{}', help='约束条件JSON')
    parser.add_argument('--output-diagram', action='store_true', help='输出架构图')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    args = parser.parse_args()
    
    try:
        constraints = json.loads(args.constraints)
    except json.JSONDecodeError:
        constraints = {}
    
    result = suggest_architecture(args.requirements, args.scale, constraints)
    result["adr"] = generate_adr(result)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("架构设计方案")
        print("=" * 60)
        
        print(f"\n架构模式: {result['pattern_name']}")
        print(f"系统规模: {result['scale']}")
        
        print("\n" + "-" * 40)
        print("核心组件:")
        for comp in result['components']:
            print(f"  • {comp['name']}: {comp['responsibility']} ({comp['tech']})")
        
        print("\n" + "-" * 40)
        print("技术栈:")
        for cat, techs in result['technology_stack'].items():
            if isinstance(techs, list):
                print(f"  {cat}: {', '.join(techs)}")
            else:
                print(f"  {cat}: {techs}")
        
        if result['extensibility']:
            print("\n" + "-" * 40)
            print("扩展性考虑:")
            for ext in result['extensibility']:
                print(f"  ✓ {ext}")
        
        print("\n" + "-" * 40)
        print("权衡分析:")
        for tw in result['tradeoffs']:
            print(f"  决策: {tw['decision']}")
            print(f"    优点: {tw['pros']}")
            print(f"    缺点: {tw['cons']}")
        
        if args.output_diagram:
            print("\n" + "-" * 40)
            print("架构图:")
            print(result['architecture_diagram'])
        
        print("\n" + "=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
