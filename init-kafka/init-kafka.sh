#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Ensure required environment variables are set
: "${KAFKA_TOPIC?Environment variable KAFKA_TOPIC must be set}"
: "${KAFKA_PARTITIONS_NUMBER?Environment variable KAFKA_PARTITIONS_NUMBER must be set}"
: "${KAFKA_REPLICATION_FACTOR?Environment variable KAFKA_REPLICATION_FACTOR must be set}"

KAFKA_DLQ_TOPIC="${KAFKA_DLQ_TOPIC:-task_generation_dlq}"

echo "============================================"
echo "Kafka Initialization Script"
echo "============================================"
echo "Main topic: $KAFKA_TOPIC"
echo "DLQ topic:  $KAFKA_DLQ_TOPIC"
echo "Partitions: $KAFKA_PARTITIONS_NUMBER"
echo "Replication: $KAFKA_REPLICATION_FACTOR"
echo ""

# Kafka CLI path
KAFKA_TOPICS="/opt/kafka/bin/kafka-topics.sh"
if [ ! -x "$KAFKA_TOPICS" ]; then
    echo "Error: kafka-topics.sh not found at $KAFKA_TOPICS" >&2
    exit 1
fi

# Function to create topic if not exists
create_topic() {
    local topic_name=$1
    local partitions=$2
    local replication=$3
    local retention_ms=${4:-604800000}  # Default: 7 days

    echo "Checking topic: $topic_name"

    if "$KAFKA_TOPICS" --list \
        --bootstrap-server kafka:9092 | grep -qw "$topic_name"; then
        echo "  Topic $topic_name already exists"

        # Get current partition count
        current_partitions=$("$KAFKA_TOPICS" \
            --bootstrap-server kafka:9092 \
            --topic "$topic_name" \
            --describe \
            2>/dev/null | grep "PartitionCount" \
            | awk -F'PartitionCount:' '{print $2}' \
            | awk '{print $1}')

        if [ -n "$current_partitions" ] && [ "$current_partitions" -lt "$partitions" ]; then
            echo "  Expanding partitions from $current_partitions to $partitions"
            "$KAFKA_TOPICS" --alter \
                --bootstrap-server kafka:9092 \
                --topic "$topic_name" \
                --partitions "$partitions"
        fi
    else
        echo "  Creating topic: $topic_name (partitions: $partitions, replication: $replication)"
        "$KAFKA_TOPICS" --create \
            --bootstrap-server kafka:9092 \
            --topic "$topic_name" \
            --partitions "$partitions" \
            --replication-factor "$replication" \
            --config retention.ms="$retention_ms" \
            --config cleanup.policy=delete
        echo "  Topic $topic_name created successfully"
    fi
}

# Create main topic
echo ""
echo "--- Creating Main Topic ---"
create_topic "$KAFKA_TOPIC" "$KAFKA_PARTITIONS_NUMBER" "$KAFKA_REPLICATION_FACTOR" 604800000

# Create DLQ topic (30-day retention for debugging)
echo ""
echo "--- Creating Dead Letter Queue Topic ---"
create_topic "$KAFKA_DLQ_TOPIC" 3 "$KAFKA_REPLICATION_FACTOR" 2592000000

# Validate main topic
echo ""
echo "--- Validation ---"
final_partitions=$("$KAFKA_TOPICS" \
    --bootstrap-server kafka:9092 \
    --topic "$KAFKA_TOPIC" \
    --describe \
    2>/dev/null | grep "PartitionCount" \
    | awk -F'PartitionCount:' '{print $2}' \
    | awk '{print $1}')

if [ -z "$final_partitions" ]; then
    echo "ERROR: Could not verify main topic $KAFKA_TOPIC" >&2
    exit 1
fi

if [ "$final_partitions" -ne "$KAFKA_PARTITIONS_NUMBER" ]; then
    echo "ERROR: Main topic has $final_partitions partitions (expected $KAFKA_PARTITIONS_NUMBER)" >&2
    exit 1
fi

# Validate DLQ topic
dlq_exists=$("$KAFKA_TOPICS" --list --bootstrap-server kafka:9092 | grep -qw "$KAFKA_DLQ_TOPIC" && echo "yes" || echo "no")
if [ "$dlq_exists" != "yes" ]; then
    echo "ERROR: DLQ topic $KAFKA_DLQ_TOPIC was not created" >&2
    exit 1
fi

echo ""
echo "============================================"
echo "Kafka initialization completed successfully!"
echo "============================================"
echo "Main topic: $KAFKA_TOPIC ($final_partitions partitions)"
echo "DLQ topic:  $KAFKA_DLQ_TOPIC"
echo ""
echo "DLQ Topic Details:"
"$KAFKA_TOPICS" --describe --topic "$KAFKA_DLQ_TOPIC" --bootstrap-server kafka:9092
echo ""

exit 0
