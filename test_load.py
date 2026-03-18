try:
    import app.main
    print("Success")
except Exception as e:
    print("Failed:")
    import traceback
    traceback.print_exc()
