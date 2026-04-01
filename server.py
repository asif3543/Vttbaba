from aiohttp import web

async def handle(request):
    return web.Response(text="🚀 Bot is Alive, Running on Render 512MB Free Tier & Connected to Supabase!")

async def web_server():
    web_app = web.Application()
    web_app.router.add_get('/', handle)
    runner = web.AppRunner(web_app)
    await runner.setup()
    # Render port 10000 require karta hai
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("🌐 Web Server Started on Port 10000")
