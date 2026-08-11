import argparse

from dotenv import load_dotenv

from social_media_manager_agent.graph import build_graph


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate social posts for the cinema")
    parser.add_argument("--mode", choices=["generic_news", "movie_release"], required=True)
    args = parser.parse_args()

    app = build_graph()
    result = app.invoke({"mode": args.mode})

    posts = result["posts"]
    print(f"Generated {len(posts)} posts:")
    for post in posts:
        print(f"- {post.title} (publish at: {post.publish_at})")

    if not posts:
        print("No posts generated: all topics found had already been covered recently.")

        return


if __name__ == "__main__":
    main()