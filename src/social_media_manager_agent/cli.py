import argparse

from dotenv import load_dotenv

from social_media_manager_agent.graph import build_graph
from social_media_manager_agent.logging_config import configure_logging


def main():
    load_dotenv()
    configure_logging()

    parser = argparse.ArgumentParser(description="Generate social posts for the cinema")
    parser.add_argument("--mode", choices=["generic_news", "movie_release"], required=True)
    args = parser.parse_args()

    app = build_graph()
    result = app.invoke({"mode": args.mode})

    posts = result["posts"]
    skipped = result.get("skipped_items", [])

    print(f"Generated {len(posts)} posts:")
    for post in posts:
        print(f"- {post.title} (publish at: {post.publish_at})")

    if skipped:
        print(f"Skipped {len(skipped)} item(s) due to errors (see log for details):")
        for title in skipped:
            print(f"- {title}")

    if not posts and not skipped:
        print("No posts generated: all topics found had already been covered recently.")

        return


if __name__ == "__main__":
    main()