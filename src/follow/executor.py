import json

from atproto import Client

from lib.aws.sqs import get_sqs_client
from lib.log import get_logger
from settings import settings

logger = get_logger(__name__)


def handler(event, context):
    """通知からフォローを取得しフォロワーのdidをSQSに投げる"""
    client = Client()
    client.login(settings.BOT_USERID, settings.BOT_APP_PASSWORD)

    # save the time in UTC when we fetch notifications
    last_seen_at = client.get_current_time_iso()
    sqs_client = get_sqs_client()

    response = client.app.bsky.notification.list_notifications()
    logger.info(f"{len(response.notifications)} notifications found.")
    for notification in response.notifications:
        if not notification.is_read and notification.reason == "follow":
            logger.info(f"{len(response.notifications)} notifications found.")
            try:
                response = sqs_client.send_message(
                    QueueUrl=settings.FOLLOWED_QUEUE_URL,
                    MessageBody=json.dumps(
                        {
                            "did": notification.author.did,
                            "handle": notification.author.handle,
                            "display_name": notification.author.display_name,
                            "cid": notification.cid,
                            "uri": notification.uri,
                            "created_at": notification.record.created_at,
                            "reason": notification.reason,
                            "avatar": notification.author.avatar,
                            "indexed_at": notification.author.indexed_at,
                        },
                        allow_nan=True,
                    ),
                )
                logger.info(
                    f"Message sent to SQS: did={notification.author.did}, message_id={response['MessageId']}"
                )
            except Exception as e:
                logger.warning(f"Failed to send message to SQS: {e}")
                continue
    # mark notifications as processed (isRead=True)
    client.app.bsky.notification.update_seen({"seen_at": last_seen_at})
    logger.info("Successfully process notification. Last seen at:", last_seen_at)
    return {"message": "OK", "status": 200}
