#!/usr/bin/env python3
"""
多阶段思考 API 服务器
实现：规划 -> 选择 -> 思考 -> 评估 -> 反馈循环
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import aiohttp
import json
import time
from datetime import datetime
import sys
import os
import re

app = Flask(__name__)
CORS(app)

# 强制清理输出缓冲 - 多重保障
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

# 禁用 Flask 的缓冲
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
app.logger.setLevel(logging.INFO)

# 加载配置
def load_config():
    with open('models_config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()
MODELS = CONFIG['models']

def log(message):
    """终端日志 - 强制刷新缓冲"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    output = f"[{timestamp}] {message}"
    # 多重刷新确保实时显示
    print(output, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    # Windows特殊处理：强制刷新
    if sys.platform == 'win32':
        import msvcrt
        try:
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_TEXT)
        except:
            pass



async def call_model(session, model_config, messages, call_id="", show_full=False, use_cache=False):
    """调用单个模型，支持prompt缓存"""
    
    # 如果启用缓存，给system和前面的user消息添加cache_control
    if use_cache and len(messages) > 0:
        # 给system消息添加缓存标记
        if messages[0].get('role') == 'system':
            messages[0]['cache_control'] = {"type": "ephemeral"}
        
        # 如果有多条消息，给倒数第二条user消息也添加缓存（通常是用户问题+历史摘要）
        if len(messages) >= 2:
            for i in range(len(messages) - 1):
                if messages[i].get('role') == 'user':
                    messages[i]['cache_control'] = {"type": "ephemeral"}
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {model_config['api_key']}"
    }
    
    # 根据调用类型优化max_tokens
    if "质检" in call_id or "摘要" in call_id:
        max_tokens = 300  # 摘要和质检不需要太多token
    elif "步骤" in call_id:
        max_tokens = 600  # 思考步骤限制400字，约600 tokens
    else:
        max_tokens = CONFIG.get('max_tokens', 2000)
    
    payload = {
        "model": model_config['model'],
        "messages": messages,
        "temperature": CONFIG.get('temperature', 0.7),
        "max_tokens": max_tokens
    }
    
    try:
        log(f"🚀 {call_id} 调用 [{model_config['name']}]" + (" [缓存]" if use_cache else ""))
        async with session.post(model_config['api_url'], json=payload, headers=headers) as response:
            response_text = await response.text()
            if response.status == 200:
                data = json.loads(response_text)
                content = data['choices'][0]['message'].get('content', '')
                
                # 显示缓存使用情况
                usage = data.get('usage', {})
                if use_cache and 'cache_read_input_tokens' in usage:
                    cache_hit = usage.get('cache_read_input_tokens', 0)
                    cache_create = usage.get('cache_creation_input_tokens', 0)
                    if cache_hit > 0:
                        log(f"💾 缓存命中: {cache_hit} tokens")
                    if cache_create > 0:
                        log(f"📝 缓存创建: {cache_create} tokens")
                
                # 根据参数决定是否显示完整内容
                if show_full:
                    log(f"✅ {call_id} 完成")
                    log("=" * 80)
                    log("📝 模型输出内容:")
                    log(content)
                    log("=" * 80)
                else:
                    log(f"✅ {call_id} 完成: {content[:50]}...")
                return {"success": True, "content": content}
            else:
                log(f"❌ {call_id} 失败: HTTP {response.status}")
                return {"success": False, "error": f"HTTP {response.status}"}
    except Exception as e:
        log(f"❌ {call_id} 异常: {str(e)}")
        return {"success": False, "error": str(e)}

# 优化线程已删除，聚焦主线程

async def generate_middle_summary(session, outputs, start_idx, end_idx, user_message):
    """生成中间轮次的摘要"""
    if start_idx >= end_idx:
        return ""
    
    # 合并中间轮次的内容
    middle_content = []
    total_chars = 0
    for i in range(start_idx, end_idx):
        if i < len(outputs):
            middle_content.append(f"第{i+1}轮：{outputs[i]}")
            total_chars += len(outputs[i])
    
    if not middle_content:
        return ""
    
    combined_content = "\n\n".join(middle_content)
    log(f"      📝 原始内容: {total_chars}字 → 准备压缩...")
    
    # 使用小模型生成摘要
    summarizer = MODELS['qwen2_7b']
    
    messages = [
        {"role": "system", "content": """# AI上下文工程大师

## 核心原则
信息密度 > 信息长度 | 结构化 > 平铺直叙

## 工作流程
1. **分析** - 理解原始内容和目标
2. **筛选** - 按关联度(1-5)、重要性(1-5)、新颖性(1-5)评分筛选
3. **精炼** - 总结提炼、实体提取、关系映射
4. **结构化** - 按指定格式组织输出

## 输出格式
```markdown
## 核心摘要
[2-3句核心结论]

## 关键推理链
- 步骤1 → 步骤2 → 结论

## 重要发现
- [分类]: [具体信息]

## 转折点
- [关键突破或方向转变]
```"""},
        {"role": "user", "content": f"""【用户问题】：
{user_message}

【中间轮次内容】：
{combined_content}

【任务】：
将上述中间轮次的思考内容压缩成高密度摘要。
- 提取核心结论和关键推理链
- 保留重要发现和转折点
- 去除重复、冗余、过渡句
- 信息密度优先，长度次要

输出摘要："""}
    ]
    
    result = await call_model(session, summarizer, messages, "中间摘要", show_full=False)
    
    if result.get('success'):
        summary = result['content'].strip()
        compression_rate = (1 - len(summary) / total_chars) * 100 if total_chars > 0 else 0
        log(f"      ✅ 摘要完成: {len(summary)}字 (压缩率: {compression_rate:.1f}%)")
        log(f"      📄 摘要内容:\n{summary}")
        return summary
    else:
        # 失败时返回简化版
        log(f"      ⚠️ 摘要生成失败，使用简化版")
        return f"【中间轮次摘要】第{start_idx+1}-{end_idx}轮的关键内容"

async def get_recent_context(session, all_outputs, step_num, user_message):
    """智能上下文管理：动态摘要+完整保留"""
    log(f"\n🧠 构建步骤{step_num}的智能上下文...")
    
    if step_num == 1:
        # 第1轮：无上下文
        log("  → 第1轮：无上下文")
        return ""
    elif step_num == 2:
        # 第2轮：第1轮完整
        log("  → 第2轮：第1轮完整")
        if all_outputs:
            return f"【第1轮思考】\n{all_outputs[0]}"
        return ""
    elif step_num == 3:
        # 第3轮：第1轮+第2轮完整
        log("  → 第3轮：第1-2轮完整")
        context_parts = []
        if len(all_outputs) >= 1:
            context_parts.append(f"【第1轮思考】\n{all_outputs[0]}")
        if len(all_outputs) >= 2:
            context_parts.append(f"【第2轮思考】\n{all_outputs[1]}")
        return "\n\n".join(context_parts)
    else:
        # 第4轮+：第1轮完整 + 中间摘要 + 最近2轮完整
        log(f"  → 第{step_num}轮：智能上下文组装")
        context_parts = []
        
        # 1. 第1轮完整（核心，永久保留）
        if len(all_outputs) >= 1:
            context_parts.append(f"【第1轮思考】\n{all_outputs[0]}")
            log(f"    ✅ 第1轮完整保留 ({len(all_outputs[0])}字)")
        
        # 2. 中间轮次摘要（第2轮到倒数第3轮）
        if step_num > 4:  # 只有超过4轮才有中间轮次
            middle_start = 1  # 第2轮开始（索引1）
            middle_end = step_num - 3  # 到倒数第3轮（不包含最近2轮）
            if middle_end > middle_start:
                log(f"    🔄 生成第{middle_start+1}-{middle_end}轮摘要...")
                middle_summary = await generate_middle_summary(session, all_outputs, middle_start, middle_end, user_message)
                if middle_summary:
                    context_parts.append(middle_summary)
                    log(f"    ✅ 中间摘要生成完成 ({len(middle_summary)}字)")
        
        # 3. 最近2轮完整（保持连贯性）
        recent_start = max(0, step_num - 3)  # 倒数第2轮
        for i in range(recent_start, step_num - 1):  # 不包含当前轮
            if i < len(all_outputs):
                context_parts.append(f"【第{i+1}轮思考】\n{all_outputs[i]}")
                log(f"    ✅ 第{i+1}轮完整保留 ({len(all_outputs[i])}字)")
        
        final_context = "\n\n".join(context_parts)
        log(f"  📊 上下文组装完成，总长度: {len(final_context)} 字符")
        return final_context

async def validate_step_async(session, step_content, user_message, step_num):
    """异步验证线程：反例生成 + 投票对抗机制"""
    log(f"\n" + "🔍" * 40)
    log(f"[验证线程] 步骤{step_num} - 启动反例对抗验证")
    log("🔍" * 40)
    log(f"📝 [验证线程] 主线程输出长度: {len(step_content)} 字符")
    
    # ========== 阶段1：生成反例（3个Qwen2.5-7B并行） ==========
    log(f"\n🎭 [阶段1] 启动3个反例生成器（Qwen2.5-7B）...")
    
    counterexample_generators = [
        MODELS['qwen2_5_7b'],
        MODELS['qwen2_5_7b'],
        MODELS['qwen2_5_7b']
    ]
    
    # 反例生成prompt（只给当前步骤+用户指令）
    counterexample_prompt = f"""【用户问题】：
{user_message}

【主线程的思考】：
{step_content}

【你的任务】：
你是反例生成专家，专门"对着干"。请针对主线程的思考，生成一个有力的反例或反驳观点。

要求：
1. 找出主线程思考的漏洞、盲点、错误
2. 提出相反的观点或反例
3. 逻辑严密，有理有据
4. 不要重复主线程的内容

输出格式：
【反例】
[你的反驳观点或反例]"""
    
    # 并行生成3个反例
    counterexample_tasks = []
    for i, generator in enumerate(counterexample_generators):
        messages = [
            {"role": "system", "content": "你是反例生成专家，专门找漏洞、提反驳。"},
            {"role": "user", "content": counterexample_prompt}
        ]
        counterexample_tasks.append(
            call_model(session, generator, messages, f"反例生成器{i+1}", show_full=False)
        )
    
    counterexample_results = await asyncio.gather(*counterexample_tasks)
    
    # 提取反例内容
    counterexamples = []
    for i, result in enumerate(counterexample_results):
        if result.get('success'):
            content = result['content'].strip()
            counterexamples.append(content)
            log(f"  ✅ 反例{i+1}生成完成 ({len(content)}字)")
            log(f"     📄 内容预览: {content[:100]}...")
        else:
            log(f"  ❌ 反例{i+1}生成失败")
    
    if not counterexamples:
        log(f"⚠️  [验证线程] 反例生成全部失败，跳过验证")
        return True, None
    
    # ========== 阶段2：投票对抗（3个GLM-4-9B并行） ==========
    log(f"\n🗳️  [阶段2] 启动3个投票器（GLM-4-9B）...")
    
    voters = [
        MODELS['glm4_9b'],
        MODELS['glm4_9b'],
        MODELS['glm4_9b']
    ]
    
    # 投票prompt（包含主线程输出+3个反例+用户指令）
    counterexamples_text = "\n\n".join([
        f"【反例{i+1}】\n{ce}" for i, ce in enumerate(counterexamples)
    ])
    
    voting_prompt = f"""【用户问题】：
{user_message}

【主线程的思考】：
{step_content}

【反例观点】：
{counterexamples_text}

【投票任务】：
你是公正的评审专家。请综合评估主线程的思考和反例观点，判断谁更有道理。

评分标准：
- 主线程：逻辑正确、紧扣问题、有价值
- 反例：找到了真实的漏洞或盲点

投票规则：
✅ 投给主线程：主线程思考正确，反例站不住脚
❌ 投给反例：反例找到了真实问题，主线程需要改进

输出格式：
投票：[主线程/反例]
理由：[一句话说明]"""
    
    # 并行投票
    voting_tasks = []
    for i, voter in enumerate(voters):
        messages = [
            {"role": "system", "content": "你是公正的评审专家，客观评判。"},
            {"role": "user", "content": voting_prompt}
        ]
        voting_tasks.append(
            call_model(session, voter, messages, f"投票器{i+1}", show_full=False)
        )
    
    voting_results = await asyncio.gather(*voting_tasks)
    
    # 统计投票
    main_votes = 0
    counter_votes = 0
    vote_reasons = []
    
    log(f"\n📊 [投票统计]：")
    for i, result in enumerate(voting_results):
        if result.get('success'):
            content = result['content']
            if "主线程" in content and "反例" not in content.split("投票：")[1].split("\n")[0]:
                main_votes += 1
                log(f"  ✅ 投票器{i+1}：投给主线程")
            else:
                counter_votes += 1
                log(f"  ❌ 投票器{i+1}：投给反例")
                # 提取理由
                if "理由：" in content:
                    reason = content.split("理由：")[1].strip()
                    vote_reasons.append(f"投票器{i+1}: {reason}")
                    log(f"     💬 理由: {reason}")
    
    log(f"\n📊 [最终结果] 主线程: {main_votes}票 | 反例: {counter_votes}票")
    
    # 判断是否需要打断（2票或3票投主线程就通过）
    if main_votes >= 2:
        log(f"✅ [验证线程] 主线程通过（{main_votes}/3票），继续")
        log("🔍" * 40 + "\n")
        return True, None
    else:
        log(f"⚠️  [验证线程] 主线程失败（仅{main_votes}/3票），打断")
        
        # 整合反例作为反馈
        feedback_parts = ["【反例观点】"]
        for i, ce in enumerate(counterexamples):
            feedback_parts.append(f"\n反例{i+1}：{ce}")
        
        feedback = "\n".join(feedback_parts)
        log("🔍" * 40 + "\n")
        
        return False, feedback

async def think_step(session, step_num, recent_context, user_message):
    """思考一个步骤（400字限制）- 简化版"""
    log("\n" + "=" * 80)
    log(f"💭 步骤 {step_num}")
    log("=" * 80)
    
    thinker = MODELS['planner']
    
    # 统一的高密度思考prompt
    system_prompt = """你是一个深度思考专家。

核心任务：回答用户的问题，不要偏离主题。

重要规则：
1. 每个步骤限制400字
2. 紧扣用户问题，不要发散
3. 进行深度多轮思考，充分分析后才能完成
4. 只有在完全解决问题后才能标注【完成】
5. 思考轮次无上限，需要多少轮就思考多少轮

思考密度要求（每句话必须有价值）：
✅ 每句话都必须推进思考
✅ 每句话都是新信息或新推理
✅ 直接给出分析，不要铺垫

严禁输出（0容忍）：
❌ 重复已说过的内容
❌ 空洞的过渡句（"接下来"、"然后"、"综上所述"）
❌ 无意义的总结和复述
❌ 与问题无关的延伸
❌ 啰嗦的解释和废话

格式：
- 完成时：[思考内容]【完成】
- 继续时：[思考内容]【继续】"""

    # 构建消息：每轮都重复原始问题，防止偏离
    user_content = f"【用户的原始问题】：{user_message}"
    if recent_context:
        user_content += f"\n\n【之前的思考摘要】：\n{recent_context}"
    
    # 强调当前轮次
    user_content += f"\n\n【当前任务】：这是第{step_num}轮思考。继续深入分析，只有完全解决问题后才标注【完成】。"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    
    if recent_context:
        log("📦 注入的上下文:")
        log(recent_context)
        log("")
    
    log(f"🚀 开始思考...")
    log(f"📋 使用模型: {thinker['name']}")
    result = await call_model(session, thinker, messages, f"步骤{step_num}", show_full=True, use_cache=True)
    
    if not result.get('success'):
        log(f"❌ 思考失败")
        return None, False, False
    
    content = result['content']
    
    # 检查是否完成
    is_complete = "【完成】" in content
    need_continue = "【继续】" in content
    
    log("\n" + "=" * 80)
    log(f"✅ 步骤{step_num}完成" + (" [最终答案]" if is_complete else " [需要继续]"))
    log("=" * 80)
    log("📝 输出内容:")
    log(content)
    log("=" * 80 + "\n")
    
    return content, is_complete, need_continue

async def single_thinking_thread(user_message, thread_id, session):
    """单个思考线程"""
    log(f"\n🧵 [线程{thread_id}] 启动思考流程")
    
    # 三线程架构
    all_outputs = []  # 保存所有步骤的原始输出
    final_answers = []  # 保存优化后的答案（返回给前端）
    
    step_num = 0
    is_complete = False
    
    # 后台验证线程管理
    pending_validations = {}  # {step_num: validation_task}
    validation_results = {}  # {step_num: (passed, feedback)}
    
    while not is_complete:
        step_num += 1
        
        log(f"\n🧵 [线程{thread_id}] 步骤 {step_num}")
        
        # 获取智能上下文（动态摘要+完整保留）
        recent_context = await get_recent_context(session, all_outputs, step_num, user_message)
        
        # 主线程：正常思考
        answer, model_complete, need_continue = await think_step(session, step_num, recent_context, user_message)
        
        if not answer:
            log(f"⚠️  [线程{thread_id}] 步骤{step_num}思考失败")
            continue
        
        # 清理答案
        clean_answer = answer
        if "【继续】" in clean_answer:
            clean_answer = clean_answer.split("【继续】")[0].strip()
        if "【完成】" in clean_answer:
            clean_answer = clean_answer.replace("【完成】", "").strip()
        
        # 保存输出（不等待验证）
        all_outputs.append(clean_answer)
        final_answers.append(clean_answer)
        log(f"💾 [线程{thread_id}] 步骤{step_num}输出已保存")
        
        # 启动后台验证线程（不等待）
        current_step_for_validation = step_num
        current_answer_for_validation = clean_answer
        
        async def validate_in_background():
            """后台验证线程 - 发现问题时直接打断主线程"""
            nonlocal is_complete, step_num, all_outputs, final_answers
            
            passed, feedback = await validate_step_async(
                session, current_answer_for_validation, user_message, current_step_for_validation
            )
            
            if not passed:
                # 验证失败，打断主线程
                log(f"\n🚨 [线程{thread_id}] 步骤{current_step_for_validation}验证失败！")
                if current_step_for_validation < len(all_outputs):
                    all_outputs[current_step_for_validation - 1] = None  # 标记为需要重做
                    validation_results[current_step_for_validation] = (False, feedback)
        
        pending_validations[step_num] = asyncio.create_task(validate_in_background())
        
        # 主线程继续，不等待验证结果
        
        # 只检查主模型判断
        if model_complete:
            log(f"✅ [线程{thread_id}] 主模型判断：已完成")
            is_complete = True
        
        # 检查是否完成
        if is_complete:
            break
    
    # 等待所有验证完成
    if pending_validations:
        await asyncio.gather(*pending_validations.values(), return_exceptions=True)
    
    log(f"\n✅ [线程{thread_id}] 思考流程完成，共{len(final_answers)}步")
    
    return {
        'thread_id': thread_id,
        'steps': final_answers,
        'total_steps': len(final_answers)
    }

async def multi_stage_thinking(user_message):
    """多阶段思考主流程 - 三重并行架构"""
    log(f"🎯 开始三重并行思考流程")
    log(f"🧵 启动3个独立思考线程...")
    log("")
    
    start_time = time.time()
    
    connector = aiohttp.TCPConnector(limit=150, limit_per_host=150)  # 增加连接数
    timeout = aiohttp.ClientTimeout(total=600)  # 增加超时时间
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 并行启动3个独立思考线程
        thread_tasks = [
            asyncio.create_task(single_thinking_thread(user_message, 1, session)),
            asyncio.create_task(single_thinking_thread(user_message, 2, session)),
            asyncio.create_task(single_thinking_thread(user_message, 3, session))
        ]
        
        log(f"⏳ 等待3个线程完成...")
        
        # 等待所有线程完成
        thread_results = await asyncio.gather(*thread_tasks, return_exceptions=True)
        
        log("\n" + "🎉" * 40)
        log(f"三重并行思考完成！")
        log("🎉" * 40 + "\n")
        
        # 合并所有线程的结果
        all_thread_outputs = []
        for result in thread_results:
            if isinstance(result, dict):
                thread_id = result['thread_id']
                steps = result['steps']
                total = result['total_steps']
                log(f"✅ 线程{thread_id}: {total}步")
                all_thread_outputs.append({
                    'thread_id': thread_id,
                    'steps': steps
                })
        
        log("\n📦 准备前端返回内容...")
        
        # 格式化输出：每个线程的内容
        formatted_answers = []
        
        for thread_data in all_thread_outputs:
            thread_id = thread_data['thread_id']
            steps = thread_data['steps']
            
            # 添加线程标题
            formatted_answers.append(f"\n{'='*60}")
            formatted_answers.append(f"【思考线程 {thread_id}】")
            formatted_answers.append(f"{'='*60}\n")
            
            # 添加每一步
            step_labels = ["第一步", "第二步", "第三步", "第四步", "第五步", "第六步", "第七步", "第八步", "第九步", "第十步"]
            for i, answer in enumerate(steps):
                clean = answer.replace("[思考内容]", "").strip()
                if i < len(step_labels):
                    formatted = f"【{step_labels[i]}】\n{clean}"
                else:
                    formatted = f"【第{i+1}步】\n{clean}"
                formatted_answers.append(formatted)
        
        # 收集3个线程的原始内容
        thread1_content = "\n\n".join([step for thread in all_thread_outputs if thread['thread_id'] == 1 for step in thread['steps']])
        thread2_content = "\n\n".join([step for thread in all_thread_outputs if thread['thread_id'] == 2 for step in thread['steps']])
        thread3_content = "\n\n".join([step for thread in all_thread_outputs if thread['thread_id'] == 3 for step in thread['steps']])
        
        log(f"\n🔄 开始智能融合3个线程的内容...")
        log(f"📊 线程1: {len(thread1_content)}字")
        log(f"📊 线程2: {len(thread2_content)}字")
        log(f"📊 线程3: {len(thread3_content)}字")
        
        # 使用KAT-Coder融合3个线程的内容
        fusion_model = MODELS['step_selector']  # KAT-Coder-Exp-72B-1010
        
        fusion_prompt = f"""【用户问题】：
{user_message}

【线程1的思考内容】：
{thread1_content}

【线程2的思考内容】：
{thread2_content}

【线程3的思考内容】：
{thread3_content}

【融合任务】：
你现在需要智能融合这3个独立思考线程的内容，生成一个完整、连贯、高质量的最终答案。

融合要求：
1. 提取3个线程的共同结论和核心观点
2. 整合不同线程的独特见解和补充信息
3. 解决线程之间的矛盾或分歧（如果有）
4. 组织成逻辑清晰、结构完整的答案
5. 保留关键的推理过程和重要细节
6. 去除重复和冗余内容

输出格式：
直接输出融合后的完整答案，不要添加"融合结果"等标题。"""

        fusion_messages = [
            {"role": "system", "content": "你是内容融合专家，擅长整合多个思考线程的内容。"},
            {"role": "user", "content": fusion_prompt}
        ]
        
        log(f"🤖 调用KAT-Coder进行智能融合...")
        fusion_result = await call_model(session, fusion_model, fusion_messages, "内容融合", show_full=False)
        
        if fusion_result.get('success'):
            final_output = fusion_result['content'].strip()
            log(f"✅ 融合完成！最终内容: {len(final_output)}字")
        else:
            log(f"⚠️  融合失败，返回原始拼接内容")
            final_output = "\n\n".join(formatted_answers)
        
        elapsed = time.time() - start_time
        log(f"\n⏱️  完成！总耗时 {elapsed:.2f}s")
        log(f"📤 返回给前端：智能融合后的最终答案")
        
        return final_output, elapsed

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
def chat_completions():
    """兼容 OpenAI 格式的聊天接口"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        log(f"📥 收到请求")
        
        messages = data.get('messages', [])
        if not messages:
            return jsonify({"error": {"message": "messages is required"}}), 400
        
        user_message = messages[-1].get('content', '')
        log(f"💬 用户消息: {user_message[:50]}...")
        
        # 执行多阶段思考
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result, elapsed = loop.run_until_complete(multi_stage_thinking(user_message))
        loop.close()
        
        # 返回 OpenAI 格式响应
        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": CONFIG.get('service_model', 'multi-stage-thinking'),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result
                },
                "finish_reason": "stop",
                "logprobs": None
            }],
            "usage": {
                "prompt_tokens": len(user_message),
                "completion_tokens": len(result),
                "total_tokens": len(user_message) + len(result)
            }
        }
        
        log(f"📤 返回响应，内容长度: {len(result)} 字符")
        return jsonify(response), 200
        
    except Exception as e:
        import traceback
        log(f"❌ 错误: {str(e)}")
        log(f"❌ 详细: {traceback.format_exc()}")
        return jsonify({"error": {"message": str(e)}}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 多阶段思考 API 服务器")
    print("="*80)
    print(f"📍 API 地址: http://127.0.0.1:8000/v1/chat/completions")
    print(f"🤖 服务模型: {CONFIG.get('service_model')}")
    print("="*80)
    print("📋 思考流程:")
    print("   1. 模型自己控制，每步400字限制")
    print("   2. 模型自己生成摘要+标题（不计入400字）")
    print("   3. 下一步只给：用户指令 + 所有摘要标题 + 摘要库")
    print("   4. 模型自己选择需要的摘要并注入")
    print("   5. 直到模型输出【完成】")
    print("="*80)
    print("🔧 使用的模型:")
    print(f"   全部使用: {MODELS['planner']['name']}")
    print("="*80 + "\n")
    
    log("🎬 服务器启动中...")
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)
