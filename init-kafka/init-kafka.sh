#!/bin/bash

# 确保所有必要的环境变量都已设置
: "${KAFKA_TOPIC?Environment variable KAFKA_TOPIC must be set}"
: "${KAFKA_PARTITIONS_NUMBER?Environment variable KAFKA_PARTITIONS_NUMBER must be set}"
: "${KAFKA_REPLICATION_FACTOR?Environment variable KAFKA_REPLICATION_FACTOR must be set}"

echo "Starting Kafka initialization for topic: $KAFKA_TOPIC"
echo "Target partitions: $KAFKA_PARTITIONS_NUMBER"
echo "Replication factor: $KAFKA_REPLICATION_FACTOR"

# 检查主题是否存在
if /opt/bitnami/kafka/bin/kafka-topics.sh --list \
  --bootstrap-server kafka:9092 | grep -qw "$KAFKA_TOPIC"; then
  echo "Topic $KAFKA_TOPIC exists"
  
  # 获取当前分区数
  partitions=$(/opt/bitnami/kafka/bin/kafka-topics.sh \
    --bootstrap-server kafka:9092 \
    --topic "$KAFKA_TOPIC" \
    --describe \
    | grep "PartitionCount" \
    | awk -F'PartitionCount:' '{print $2}' \
    | awk '{print $1}')
  
  echo "Current partitions for $KAFKA_TOPIC: $partitions"
  
  # 当现有分区不足时进行扩展
  if [ -n "$partitions" ] && [ "$partitions" -lt "$KAFKA_PARTITIONS_NUMBER" ]; then
    echo "Expanding partitions from $partitions to $KAFKA_PARTITIONS_NUMBER"
    /opt/bitnami/kafka/bin/kafka-topics.sh --alter \
      --bootstrap-server kafka:9092 \
      --topic "$KAFKA_TOPIC" \
      --partitions "$KAFKA_PARTITIONS_NUMBER"
  else
    echo "Topic already has sufficient partitions ($partitions)"
  fi
else
  # 创建新主题
  echo "Creating new topic $KAFKA_TOPIC with $KAFKA_PARTITIONS_NUMBER partitions"
  /opt/bitnami/kafka/bin/kafka-topics.sh --create \
    --bootstrap-server kafka:9092 \
    --topic "$KAFKA_TOPIC" \
    --partitions "$KAFKA_PARTITIONS_NUMBER" \
    --replication-factor "$KAFKA_REPLICATION_FACTOR"
fi

# 验证最终分区数
final_partitions=$(/opt/bitnami/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 \
  --topic "$KAFKA_TOPIC" \
  --describe \
  | grep "PartitionCount" \
  | awk -F'PartitionCount:' '{print $2}' \
  | awk '{print $1}')

if [ "$final_partitions" -ne "$KAFKA_PARTITIONS_NUMBER" ]; then
  echo "Error: Failed to set partitions to $KAFKA_PARTITIONS_NUMBER. Current: $final_partitions" >&2
  exit 1
fi

echo "Kafka initialization completed successfully for topic $KAFKA_TOPIC with $final_partitions partitions"
exit 0