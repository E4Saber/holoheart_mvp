import os
import json
import time
import threading
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
def load_environment():
    # 获取当前脚本的绝对路径并加载环境变量
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    dotenv_path = os.path.join(parent_dir, '.env')
    
    # 如果.env文件存在，则加载它
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path, override=True)
    else:
        # 如果没有找到.env文件，也尝试在当前目录查找
        local_dotenv = os.path.join(script_dir, '.env')
        if os.path.exists(local_dotenv):
            load_dotenv(local_dotenv, override=True)

class ImprovedRateLimiter:
    """
    令牌桶（TokenBucket）

    """
    def __init__(self, rate_limit=2, time_window=1, max_retries=3, retry_delay=1):
        """
        增强型速率限制器
        :param rate_limit: 在时间窗口内允许的请求数
        :param time_window: 时间窗口（秒）
        :param max_retries: 遇到限流时最大重试次数
        :param retry_delay: 重试延迟基数（秒），实际延迟会随重试次数增加
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.tokens = rate_limit
        self.last_refill_time = time.time()
        self.lock = threading.Lock()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.last_request_time = 0  # 记录上次请求时间
    
    def acquire(self):
        """尝试获取一个令牌"""
        with self.lock:
            current_time = time.time()
            
            # 确保请求间隔至少有一定时间
            min_interval = self.time_window / self.rate_limit
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < min_interval:
                sleep_time = min_interval - time_since_last_request
                time.sleep(sleep_time)
                current_time = time.time()  # 更新当前时间
            
            # 计算从上次补充令牌到现在应该补充的令牌数
            time_passed = current_time - self.last_refill_time
            new_tokens = int(time_passed / self.time_window * self.rate_limit)
            
            if new_tokens > 0:
                self.tokens = min(self.rate_limit, self.tokens + new_tokens)
                self.last_refill_time = current_time
            
            if self.tokens > 0:
                self.tokens -= 1
                self.last_request_time = time.time()  # 更新上次请求时间
                return True
            return False
    
    def wait_for_token(self, timeout=30):
        """等待直到获取到令牌或超时"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.acquire():
                return True
            time.sleep(0.1)
        return False

    def execute_with_retry(self, func, *args, **kwargs):
        """使用重试逻辑执行函数，针对Kimi API的429错误进行特殊处理"""
        for attempt in range(self.max_retries + 1):
            try:
                # 等待获取令牌
                if not self.wait_for_token():
                    if attempt == self.max_retries:
                        raise Exception("获取令牌超时，请稍后再试")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                # 执行函数
                return func(*args, **kwargs)
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # 检查是否是速率限制错误
                if "rate_limit" in error_str and attempt < self.max_retries:
                    # 解析API返回的等待时间建议
                    wait_time = 1.0  # 默认等待1秒
                    
                    # 尝试从错误消息中提取等待时间
                    import re
                    time_match = re.search(r'after (\d+) seconds', str(e))
                    if time_match:
                        suggested_wait = int(time_match.group(1))
                        # 增加一点额外时间以确保安全
                        wait_time = suggested_wait + 0.5
                    else:
                        # 如果无法提取，使用指数退避策略
                        wait_time = max(1.0, self.retry_delay * (2 ** attempt))
                    
                    print(f"遇到速率限制，等待 {wait_time:.2f} 秒后重试 (尝试 {attempt+1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    raise  # 如果不是速率限制错误或已达到最大重试次数，则抛出异常

class KimiAPI:
    def __init__(self, api_key=None, api_url=None, rate_limit=2, time_window=1.5):
        """
        初始化Kimi API客户端
        :param api_key: Kimi API密钥，如果为None则从环境变量读取
        :param api_url: Kimi API URL，如果为None则从环境变量读取
        :param rate_limit: 速率限制（每个时间窗口的请求数）
        :param time_window: 时间窗口（秒）
        """
        # 加载环境变量
        load_environment()
        
        # 设置API配置
        self.api_url = api_url or os.getenv('KIMI_API_URL', 'https://api.moonshot.cn/v1')
        self.api_key = api_key or os.getenv('KIMI_API_KEY', '')
        
        # 创建限流器
        self.api_limiter = ImprovedRateLimiter(rate_limit=rate_limit, time_window=time_window)
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url
        )
        
        # 定义工具
        self.tools = [
            {
                "type": "builtin_function",
                "function": {
                    "name": "$web_search"
                },
            }
        ]

        # 添加请求计数器，帮助调试
        self.request_count = 0
        self.last_request_time = 0
    
    def rate_limited_api_call(self, func, *args, **kwargs):
        """使用限流器包装API调用"""
        if not self.api_limiter.wait_for_token():
            raise Exception("API请求超时，请稍后再试")
        return func(*args, **kwargs)
    
    def search_impl(self, arguments):
        """执行网络搜索的实现"""
        print(f"执行网络搜索，参数: {arguments}")
        return arguments
    
    def chat(self, message, history=None):
        """
        发送聊天请求并获取完整响应
        :param message: 用户消息
        :param history: 聊天历史
        :return: 聊天响应
        """
        history = history or []
        
        # 初始化消息数组
        messages = [
            {"role": "system", "content": "你是 Kimi"},
            *history,
            {"role": "user", "content": message}
        ]
        
        return self.process_chat_request(messages)
    
    def stream_chat(self, message, history=None):
        """
        发送流式聊天请求并以生成器形式返回响应
        :param message: 用户消息
        :param history: 聊天历史
        :return: 生成器，产生流式聊天响应
        """
        history = history or []
        
        # 初始化消息数组
        messages = [
            {"role": "system", "content": "你是 Kimi"},
            *history,
            {"role": "user", "content": message}
        ]
        
        return self.process_stream_chat(messages)
    
    def process_chat_request(self, messages):
        """处理聊天请求的核心逻辑 - 优化版：直接使用一次请求完成工具调用"""
        try:
            # 记录这是第几个请求
            self.request_count += 1
            request_id = self.request_count
            
            # 计算距离上次请求的时间间隔
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            self.last_request_time = current_time
            
            print(f"请求 #{request_id} - 距上次请求: {time_since_last:.2f}秒")

            # 使用限流的API调用
            completion = self.api_limiter.execute_with_retry(
                self.client.chat.completions.create,
                model="kimi-latest",
                messages=messages,
                temperature=0.3,
                max_tokens=10000,
                tools=self.tools,
                stream=False
            )
            
            choice = completion.choices[0]
            finish_reason = choice.finish_reason
            
            # 处理工具调用
            if finish_reason == "tool_calls":
                print(f"请求 #{request_id} - 需要调用工具")
                
                # 添加assistant消息
                messages.append(choice.message.model_dump())
                
                # 处理工具调用
                for tool_call in choice.message.tool_calls:
                    tool_call_name = tool_call.function.name
                    tool_call_arguments = json.loads(tool_call.function.arguments)
                    
                    if tool_call_name == "$web_search":
                        tool_result = self.search_impl(tool_call_arguments)
                    else:
                        tool_result = f"Error: unable to find tool by name '{tool_call_name}'"
                    
                    # 添加工具响应消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call_name,
                        "content": json.dumps(tool_result)
                    })
                
                # 在调用第二次API之前增加额外延迟，确保不会触发速率限制
                # time.sleep(1.0)
                
                print(f"请求 #{request_id} - 发送后续请求获取最终结果")
                
                # 使用更新后的消息再次调用API获取最终结果
                final_completion = self.api_limiter.execute_with_retry(
                    self.client.chat.completions.create,
                    model="kimi-latest",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=10000,
                    stream=False
                )
                
                print(f"请求 #{request_id} - 处理完成")
                return final_completion.choices[0].message.content
            else:
                # 无工具调用，直接返回结果
                print(f"请求 #{request_id} - 无需工具调用，直接返回结果")
                return choice.message.content
                
        except Exception as e:
            print(f"处理聊天请求时出错: {str(e)}")
            raise
    
    async def process_stream_chat(self, messages):
        """使用循环结构处理工具调用的流式响应，同时保证普通响应也是流式的"""
        response_id = f"chatcmpl-{int(time.time() * 1000)}"
        self.request_count += 1
        request_id = self.request_count
        
        # 发送响应开始标记
        yield {'type': 'start', 'id': response_id}
        
        try:
            print(f"流式请求 #{request_id} - 开始")
            
            # 第一步：检查是否需要工具调用 (非流式)
            try:
                completion = self.api_limiter.execute_with_retry(
                    self.client.chat.completions.create,
                    model="kimi-latest",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=10000,
                    tools=self.tools,
                    stream=False
                )
                
                choice = completion.choices[0]
                finish_reason = choice.finish_reason
                
                if finish_reason == "tool_calls":
                    # 有工具调用
                    print(f"流式请求 #{request_id} - 需要工具调用")
                    yield {'type': 'tool_call', 'id': response_id, 'content': '正在搜索相关信息...'}
                    
                    # 添加assistant消息
                    messages.append(choice.message.model_dump())
                    
                    # 处理所有工具调用
                    for tool_call in choice.message.tool_calls:
                        tool_call_name = tool_call.function.name
                        tool_call_arguments = json.loads(tool_call.function.arguments)
                        
                        if tool_call_name == "$web_search":
                            tool_result = self.search_impl(tool_call_arguments)
                        else:
                            tool_result = f"Error: unable to find tool by name '{tool_call_name}'"
                        
                        # 添加工具响应消息
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call_name,
                            "content": json.dumps(tool_result)
                        })
                    
                    # 确保在工具调用后有足够的间隔时间
                    # time.sleep(1.5)
                    
                    # 使用更新后的消息获取最终流式回答
                    print(f"流式请求 #{request_id} - 工具调用后的流式响应")
                else:
                    # 无工具调用，但我们仍需要使用流式响应
                    print(f"流式请求 #{request_id} - 无需工具调用，切换到流式模式")
                    # 不需要任何操作，直接继续使用原始消息
                
                # 不论是否有工具调用，都使用流式模式获取最终响应
                stream = self.api_limiter.execute_with_retry(
                    self.client.chat.completions.create,
                    model="kimi-latest",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=10000,
                    stream=True  # 始终使用流式
                )
                
                # 处理流式响应
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield {
                            'type': 'chunk',
                            'id': response_id,
                            'content': delta.content
                        }
            
            except Exception as e:
                error_msg = f"API调用错误: {str(e)}"
                print(error_msg)
                yield {'type': 'error', 'id': response_id, 'error': error_msg}
                
        except Exception as e:
            error_msg = str(e)
            print(f"流式响应生成错误: {error_msg}")
            yield {'type': 'error', 'id': response_id, 'error': error_msg}
        
        finally:
            print(f"流式请求 #{request_id} - 结束")
            yield {'type': 'end', 'id': response_id}

    # def process_stream_chat(self, messages):
    #     """使用循环结构处理工具调用的流式响应"""
    #     response_id = f"chatcmpl-{int(time.time() * 1000)}"
    #     self.request_count += 1
    #     request_id = self.request_count
        
    #     # 发送响应开始标记
    #     yield {'type': 'start', 'id': response_id}
        
    #     try:
    #         print(f"流式请求 #{request_id} - 开始")
            
    #         finish_reason = None
    #         flag = 0  # 标记是否已经处理过工具调用
            
    #         # 使用循环处理可能的工具调用
    #         while finish_reason is None or finish_reason == "tool_calls":
    #             # 第一轮或工具调用后的请求
    #             try:
    #                 if flag == 1:
    #                     # 工具调用后，使用流式模式返回最终回答
    #                     print(f"流式请求 #{request_id} - 工具调用后的流式响应")
    #                     # 确保有足够的间隔时间
    #                     time.sleep(1.5)  
                        
    #                     stream = self.api_limiter.execute_with_retry(
    #                         self.client.chat.completions.create,
    #                         model="kimi-latest",
    #                         messages=messages,
    #                         temperature=0.3,
    #                         max_tokens=10000,
    #                         stream=True
    #                     )
                        
    #                     for chunk in stream:
    #                         delta = chunk.choices[0].delta
    #                         if delta.content:
    #                             yield {
    #                                 'type': 'chunk',
    #                                 'id': response_id,
    #                                 'content': delta.content
    #                             }
                        
    #                     # 流式响应完成后跳出循环
    #                     break
                        
    #                 else:
    #                     # 第一轮请求，检查是否需要工具调用
    #                     print(f"流式请求 #{request_id} - 检查是否需要工具调用")
                        
    #                     completion = self.api_limiter.execute_with_retry(
    #                         self.client.chat.completions.create,
    #                         model="kimi-latest",
    #                         messages=messages,
    #                         temperature=0.3,
    #                         max_tokens=10000,
    #                         tools=self.tools,
    #                         stream=False
    #                     )
                        
    #                     choice = completion.choices[0]
    #                     finish_reason = choice.finish_reason
                        
    #                     if finish_reason == "tool_calls":
    #                         # 有工具调用，设置标记并处理
    #                         flag = 1
    #                         print(f"流式请求 #{request_id} - 需要工具调用")
    #                         yield {'type': 'tool_call', 'id': response_id, 'content': '正在搜索相关信息...'}
                            
    #                         # 添加assistant消息
    #                         messages.append(choice.message.model_dump())
                            
    #                         # 处理所有工具调用
    #                         for tool_call in choice.message.tool_calls:
    #                             tool_call_name = tool_call.function.name
    #                             tool_call_arguments = json.loads(tool_call.function.arguments)
                                
    #                             if tool_call_name == "$web_search":
    #                                 tool_result = self.search_impl(tool_call_arguments)
    #                             else:
    #                                 tool_result = f"Error: unable to find tool by name '{tool_call_name}'"
                                
    #                             # 添加工具响应消息
    #                             messages.append({
    #                                 "role": "tool",
    #                                 "tool_call_id": tool_call.id,
    #                                 "name": tool_call_name,
    #                                 "content": json.dumps(tool_result)
    #                             })
    #                     # else:
    #                     #     # 无工具调用，直接返回结果
    #                     #     print(f"流式请求 #{request_id} - 无需工具调用")
    #                     #     content = choice.message.content
    #                     #     yield {'type': 'chunk', 'id': response_id, 'content': content}
    #                         # break
                
    #             except Exception as e:
    #                 error_msg = f"API调用错误: {str(e)}"
    #                 print(error_msg)
    #                 yield {'type': 'error', 'id': response_id, 'error': error_msg}
    #                 break
        
    #     except Exception as e:
    #         error_msg = str(e)
    #         print(f"流式响应生成错误: {error_msg}")
    #         yield {'type': 'error', 'id': response_id, 'error': error_msg}
        
    #     finally:
    #         print(f"流式请求 #{request_id} - 结束")
    #         yield {'type': 'end', 'id': response_id}