from ai.attendance.session_manager import SessionManager

def create_default():
    mgr = SessionManager()
    ok, msg, sess = mgr.create_session(
        subject="Artificial Intelligence & Machine Learning",
        department="AI",
        year=1,
        section="",
        room="LH-101",
        faculty_name="Faculty / Admin",
        regular_window_minutes=15,
        late_window_minutes=25
    )
    print(f"Session Created: {ok} -> {msg}")
    if sess:
        print(f"Active Session Code: {sess['session_code']}, QR: {sess.get('qr_image_path')}")

if __name__ == '__main__':
    create_default()
