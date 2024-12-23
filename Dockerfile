# 使用官方 Python 3.10 镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 拷贝项目文件到容器
COPY . /app

# 设置国内的 PyPI 源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装所需依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 cron
RUN apt-get update && apt-get install -y cron

# 定义构建参数
ARG student_id=22020007067
ARG categoryEnergy_id
# 将构建参数转换为环境变量
ENV student_id=${student_id}
ENV categoryEnergy_id=${categoryEnergy_id}
# 使用环境变量
RUN echo "Student ID during build: $student_id"
RUN echo "Category Energy ID: $categoryEnergy_id"
# 初始化数据库
RUN python init.py

# 添加 cron 任务：每 10 分钟执行一次 get.py
RUN echo "*/10 * * * * python /app/get.py" > /etc/cron.d/my-cron-job

# 设置 cron 权限
RUN chmod 0644 /etc/cron.d/my-cron-job

# 启动 cron 服务
RUN crontab /etc/cron.d/my-cron-job

# 暴露 Streamlit 服务的默认端口
EXPOSE 8501

# 设置默认的启动命令
CMD ["sh", "-c", "cron && streamlit run visualize.py --server.port=8501"]