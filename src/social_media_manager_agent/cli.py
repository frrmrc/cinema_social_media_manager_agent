import argparse
import sys

from dotenv import load_dotenv

from social_media_manager_agent.graph import build_graph
from social_media_manager_agent.logging_config import configure_logging
from social_media_manager_agent.tools.publisher import publish_due_posts


def _run_generate(mode: str) -> None:
    app = build_graph()
    result = app.invoke({"mode": mode})

    posts = result["posts"]
    skipped = result.get("skipped_items", [])

    print(f"Generated {len(posts)} posts:")
    for post in posts:
        if post.approved:
            print(f"- {post.title}: approved, scheduled at {post.scheduled_at}")
        elif post.approved is False:
            print(f"- {post.title}: rejected ({post.rejection_reason})")
        else:
            print(f"- {post.title}: not reviewed")

    if skipped:
        print(f"Skipped {len(skipped)} item(s) due to errors (see log for details):")
        for title in skipped:
            print(f"- {title}")

    if not posts and not skipped:
        print("No posts generated: all topics found had already been covered recently.")


def _run_publish_due() -> None:
    published, skipped = publish_due_posts()

    print(f"Published {len(published)} post(s):")
    for title in published:
        print(f"- {title}")

    if skipped:
        print(f"Skipped {len(skipped)} post(s) (not due, not approved, or already published):")
        for title in skipped:
            print(f"- {title}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    configure_logging()

    parser = argparse.ArgumentParser(description="Generate and publish social posts for the cinema")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Discover, write, and review a batch of posts")
    generate_parser.add_argument("--mode", choices=["generic_news", "movie_release"], required=True)

    subparsers.add_parser("publish-due", help="Publish approved posts whose scheduled time has arrived")

    args = parser.parse_args()

    if args.command == "generate":
        _run_generate(args.mode)
    elif args.command == "publish-due":
        _run_publish_due()


if __name__ == "__main__":
    main()
