import argparse

from dotenv import load_dotenv

from social_media_manager_agent.graph import build_graph


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Genera post social per il cinema")
    parser.add_argument("--mode", choices=["generic_news", "movie_release"], required=True)
    args = parser.parse_args()

    app = build_graph()
    result = app.invoke({"mode": args.mode})

    posts = result["posts"]
    print(f"Generati {len(posts)} post:")
    for post in posts:
        print(f"- {post.title} (pubblicazione: {post.publish_at})")

    if not posts:
        print("Nessun post generato: tutti gli argomenti trovati erano già stati trattati di recente.")

        return


if __name__ == "__main__":
    main()