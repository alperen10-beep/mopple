import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:geolocator/geolocator.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:crypto/crypto.dart';
import 'package:uuid/uuid.dart';
import 'package:flutter/material.dart';
import 'socket_service.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:contacts_service/contacts_service.dart';
import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:intl_phone_number_input/intl_phone_number_input.dart';

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'SuperChat Pro X',
        theme: ThemeData(primarySwatch: Colors.purple),
        home: LoginScreen(),
      );
}

/// 1) Login
class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _ctrl = TextEditingController();

  void _login() {
    if (_ctrl.text.trim().isEmpty) return;
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => HomeScreen(username: _ctrl.text.trim()),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Giriş')),
        body: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextField(controller: _ctrl, decoration: InputDecoration(labelText: 'Kullanıcı Adı')),
              SizedBox(height: 20),
              ElevatedButton(onPressed: _login, child: Text('Başla'))
            ],
          ),
        ),
      );
}

/// 2) Ana ekran
class HomeScreen extends StatefulWidget {
  final String username;
  HomeScreen({required this.username});
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  late TabController _tc;

  @override
  void initState() {
    super.initState();
    _tc = TabController(length: 4, vsync: this);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text('SuperChat X (${widget.username})'),
          bottom: TabBar(
            controller: _tc,
            tabs: [
              Tab(icon: Icon(Icons.chat), text: 'Sohbet'),
              Tab(icon: Icon(Icons.circle), text: 'Durum'),
              Tab(icon: Icon(Icons.person), text: 'Profil'),
              Tab(icon: Icon(Icons.menu), text: 'Ultra'),
            ],
          ),
        ),
        body: TabBarView(
          controller: _tc,
          children: [
            ChatScreen(username: widget.username),
            StatusScreen(username: widget.username),
            ProfileScreen(username: widget.username),
            SuperMenuScreen(username: widget.username),
          ],
        ),
      );
}

class ChatScreen extends StatefulWidget {
  final String username;
  ChatScreen({required this.username});

  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late IO.Socket socket;
  final _ctrl = TextEditingController();
  List<String> _msgs = [];
  bool _typing = false;

  @override
  void initState() {
    super.initState();
    socket = IO.io('http://10.0.2.2:3000', {
      'transports': ['websocket'],
      'autoConnect': true,
    });

    socket.onConnect((_) => print('🔗 Bağlandı'));

    socket.on('receiveMessage', (data) {
      setState(() => _msgs.add('${data['username']}: ${data['msg']}'));
    });

    socket.on('typing', (user) {
      setState(() => _typing = true);
      Future.delayed(Duration(seconds: 1), () {
        setState(() => _typing = false);
      });
    });

    _loadContacts();  // Load contacts when the screen is loaded
  }

  Future<void> _checkPermissions() async {
    var status = await Permission.contacts.status;
    if (!status.isGranted) {
      await Permission.contacts.request();
    }
    if (await Permission.contacts.isGranted) {
      _loadContacts();
    } else {
      print("Kişiler verisine erişim izni verilmedi.");
    }
  }

  Future<void> _loadContacts() async {
    try {
      final contacts = await getContacts();  // Fetch contacts
      print("Contacts: $contacts");
      // Handle contacts as needed (e.g., show them in the UI)
    } catch (e) {
      print("Error loading contacts: $e");
    }
  }

  Future<List<Contact>> getContacts() async {
    try {
      // This will return a List<Contact> directly
      List<Contact> contacts = await ContactsService.getContacts();
      return contacts;
    } catch (e) {
      print("Error: $e");
      return [];
    }
  }

  void _send() {
    final text = _ctrl.text.trim();
    if (text.isEmpty) return;
    final msg = {'username': widget.username, 'msg': text};
    socket.emit('sendMessage', msg);
    setState(() => _msgs.add('Me: $text'));
    _ctrl.clear();
  }

  @override
  void dispose() {
    socket.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(children: [
        Expanded(
          child: ListView.builder(
            itemCount: _msgs.length,
            itemBuilder: (_, i) => ListTile(title: Text(_msgs[i])),
          ),
        ),
        if (_typing) Text('Diğer kişi yazıyor...'),
        Row(children: [
          IconButton(icon: Icon(Icons.translate), onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => TranslateScreen()))),
          IconButton(icon: Icon(Icons.summarize), onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => SummaryScreen()))),
          Expanded(
            child: TextField(
              controller: _ctrl,
              decoration: InputDecoration(labelText: 'Mesaj'),
              onChanged: (v) => setState(() => _typing = v.isNotEmpty),
            ),
          ),
          IconButton(icon: Icon(Icons.send), onPressed: _send),
        ]),
      ]);
}
/// 4) Durum
class StatusScreen extends StatefulWidget {
  final String username;
  StatusScreen({required this.username});
  @override
  _StatusScreenState createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  final _ctrl = TextEditingController();
  List<String> _sts = [];

  void _add() {
    if (_ctrl.text.isEmpty) return;
    setState(() => _sts.add('${widget.username}: ${_ctrl.text}'));
    _ctrl.clear();
  }

  @override
  Widget build(BuildContext context) => Column(children: [
        Expanded(
          child: ListView.builder(
            itemCount: _sts.length,
            itemBuilder: (_, i) => ListTile(title: Text(_sts[i])),
          ),
        ),
        Row(children: [
          Expanded(child: TextField(controller: _ctrl, decoration: InputDecoration(labelText: 'Durum'))),
          ElevatedButton(onPressed: _add, child: Text('Yayınla')),
        ]),
      ]);
}

/// 5) Profil
class ProfileScreen extends StatefulWidget {
  final String username;
  ProfileScreen({required this.username});
  @override
  _ProfileScreenState createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _name = TextEditingController();

  @override
  void initState() {
    super.initState();
    _name.text = widget.username;
  }

  void _save() {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Profil güncellendi')));
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.all(16),
        child: Column(children: [
          CircleAvatar(radius: 40, child: Text(widget.username[0])),
          TextField(controller: _name, decoration: InputDecoration(labelText: 'Ad')),
          SizedBox(height: 20),
          ElevatedButton(onPressed: _save, child: Text('Kaydet')),
        ]),
      );
}

/// 6) Ultra Menü
class SuperMenuScreen extends StatelessWidget {
  final String username;
  SuperMenuScreen({required this.username});
  @override
  Widget build(BuildContext context) => ListView(padding: EdgeInsets.all(16), children: [
        ListTile(leading: Icon(Icons.videocam), title: Text('Görüntülü Arama'), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => VideoCallScreen()))),
        ListTile(leading: Icon(Icons.photo), title: Text('Medya Paylaş'), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => MediaPickerScreen()))),
        ListTile(leading: Icon(Icons.location_on), title: Text('Konum Paylaş'), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LocationSharingScreen()))),
        ListTile(leading: Icon(Icons.block), title: Text('Blokzincir Kimlik'), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => BlockchainScreen()))),
        ListTile(leading: Icon(Icons.shield), title: Text('Kuantum Şifreleme'), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => QuantumStubScreen()))),
        ListTile(leading: Icon(Icons.wifi), title: Text('Mesh Offline Ağ'), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => MeshStubScreen()))),
      ]);
}

class PhoneNumberScreen extends StatefulWidget {
  @override
  _PhoneNumberScreenState createState() => _PhoneNumberScreenState();
}

class _PhoneNumberScreenState extends State<PhoneNumberScreen> {
  PhoneNumber _phoneNumber = PhoneNumber(isoCode: 'US');
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();


  void _onPhoneNumberChanged(PhoneNumber number) {
    setState(() {
      _phoneNumber = number;
    });
  }


  void _submitPhoneNumber() {
    if (_formKey.currentState?.validate() ?? false) {
      print('Onaylanan Numara: ${_phoneNumber.phoneNumber}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Telefon Numarası Girişi")),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              InternationalPhoneNumberInput(
                onInputChanged: _onPhoneNumberChanged,
                initialValue: _phoneNumber,
                selectorConfig: SelectorConfig(
                  selectorType: PhoneInputSelectorType.DIALOG,
                ),
                inputDecoration: InputDecoration(
                  labelText: 'Telefon Numarası',
                  border: OutlineInputBorder(),
                ),
              ),
              SizedBox(height: 16),
              ElevatedButton(
                onPressed: _submitPhoneNumber,
                child: Text("Onayla"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class PhoneNumberList extends StatefulWidget {
  @override
  _PhoneNumberListState createState() => _PhoneNumberListState();
}

class _PhoneNumberListState extends State<PhoneNumberList> {
  List<Contact> contacts = [];

  @override
  void initState() {
    super.initState();
    _requestPermission();
  }

  Future<void> _requestPermission() async {
    // Rehber izni isteme
    PermissionStatus permission = await Permission.contacts.request();

    if (permission.isGranted) {
      _getContacts();
    } else {
      print("Rehber izni verilmedi.");
    }
  }

  Future<void> _getContacts() async {
    try {
      // Rehberdeki kişileri al
      List<Contact> contactsList = await ContactsService.getContacts();
      setState(() {
        contacts = contactsList;
      });
    } catch (e) {
      print("Kişiler alınamadı: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Telefon Kişileri"),
      ),
      body: contacts.isEmpty
          ? Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: contacts.length,
              itemBuilder: (context, index) {
                return ListTile(
                  title: Text(contacts[index].displayName ?? "No Name"),
                  subtitle: Text(contacts[index].phones?.isEmpty ?? true
                      ? "No Phone Number"
                      : contacts[index].phones!.first.value ?? "No Phone Number"),
                );
              },
            ),
    );
  }
}

class QuantumStubScreen extends StatefulWidget {
  @override
  _QuantumStubScreen createState() => _QuantumStubScreen(); 
}

class _QuantumStubScreen extends State<QuantumStubScreen> {
  String encryptedText = '';
  final key = encrypt.Key.fromUtf8('32karakterlikbiranahtar1234567890!!');
  final iv = encrypt.IV.fromLength(16);
  final controller = TextEditingController();


  void _encryptText() {
    final encrypter = encrypt.Encrypter(encrypt.AES(key));
    final encrypted = encrypter.encrypt(controller.text, iv: iv);
    setState(() => encryptedText = encrypted.base64);
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Kuantum Güvenli Şifreleme')),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(controller: controller, decoration: InputDecoration(labelText: 'Metin girin')),
            SizedBox(height: 10),
            ElevatedButton(onPressed: _encryptText, child: Text('Şifrele')),
            SizedBox(height: 10),
            SelectableText('Şifreli Metin (AES): $encryptedText'),
          ],
        ),
      ),
    );
  }
}

class GroupModel {
  final String id;
  final String name;
  final String description;
  final String imageUrl;
  final bool isPrivate;
  final List<String> members;

  GroupModel({
    required this.id,
    required this.name,
    required this.description,
    required this.imageUrl,
    required this.isPrivate,
    required this.members,
  });

  factory GroupModel.fromJson(Map<String, dynamic> json) {
    return GroupModel(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      imageUrl: json['imageUrl'],
      isPrivate: json['isPrivate'],
      members: List<String>.from(json['members']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'imageUrl': imageUrl,
      'isPrivate': isPrivate,
      'members': members,
    };
  }
}

/// 7) Çeviri
class TranslateScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('AI Çeviri')),
        body: Center(child: Text('Gerçek zamanlı AI çeviri entegrasyonu buraya')),
      );
}

class LocationSharingScreen extends StatefulWidget {
  @override
  _LocationSharingScreenState createState() => _LocationSharingScreenState();
}

class _LocationSharingScreenState extends State<LocationSharingScreen> {
  String _location = "Konum alınıyor...";

  // Konumu almak için
  void _getLocation() async {
    bool serviceEnabled;
    LocationPermission permission;


    // Konum verisi aktifliğini almak için kontrol et
    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      setState(() {
        _location = "Konum verisi kapalı!";
      });
      return;
    }


    // Konum izni Kontrolü 
    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission != LocationPermission.whileInUse && permission != LocationPermission.always) {
        setState(() {
          _location = "Konum izni verilmedi!";
        });
        return;
      }
    }


    // Konum bilgisini al
    Position position = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
    setState(() {
      _location = "Enlem: ${position.latitude}, Boylam: ${position.longitude}";
    });
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Konum Paylaş')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_location),
            ElevatedButton(
              onPressed: _getLocation,
              child: Text('Konumu Al'),
            ),
          ],
        ),
      ),
    );
  }
}

class GroupCreatePage extends StatefulWidget {
  @override
  _GroupCreatePageState createState() => _GroupCreatePageState();
}

class _GroupCreatePageState extends State<GroupCreatePage> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _descController = TextEditingController();
  bool _isPrivate = false;

  void _createGroup() {
    final group = {
      'id': const Uuid().v4(),
      'name': _nameController.text,
      'description': _descController.text,
      'imageUrl': '',
      'isPrivate': _isPrivate,
      'members': [],
    };


    // TODO: Backendless API ile kaydet
    print("Grup oluşturuldu: $group");


    Navigator.pop(context);
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Grup Oluştur")),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(controller: _nameController, decoration: InputDecoration(labelText: "Grup Adı")),
            TextField(controller: _descController, decoration: InputDecoration(labelText: "Açıklama")),
            SwitchListTile(
              title: Text("Gizli Grup"),
              value: _isPrivate,
              onChanged: (val) => setState(() => _isPrivate = val),
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _createGroup,
              child: Text("Grubu Oluştur"),
            ),
          ],
        ),
      ),
    );
  }
}

class Block {
  final int index;
  final String timestamp;
  final String data;
  final String previousHash;
  final String hash;


  Block(this.index, this.timestamp, this.data, this.previousHash) : hash = generateHash(index, timestamp, data, previousHash);

  static String generateHash(int index, String timestamp, String data, String previousHash) {
    final input = '$index$timestamp$data$previousHash';
    return sha256.convert(utf8.encode(input)).toString();
  }
}

class BlockchainScreen extends StatefulWidget {
  @override
  _BlockchainScreenState createState() => _BlockchainScreenState();
}

class _BlockchainScreenState extends State<BlockchainScreen> {
  List<Block> blockchain = [];

  void _addBlock() {
    final timestamp = DateTime.now().toString();
    final data = 'İşlem verisi ${blockchain.length + 1}';
    final previousHash = blockchain.isEmpty ? '0' : blockchain.last.hash;


    final newBlock = Block(blockchain.length, timestamp, data, previousHash);
    setState(() => blockchain.add(newBlock));
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Gerçekçi Blokzincir')),
      body: Column(
        children: [
          ElevatedButton(onPressed: _addBlock, child: Text("Yeni Blok Ekle")),
          Expanded(
            child: ListView.builder(
              itemCount: blockchain.length,
              itemBuilder: (context, index) {
                final block = blockchain[index];
                return ListTile(
                  title: Text('Blok ${block.index}'),
                  subtitle: Text('Hash: ${block.hash.substring(0, 20)}...'),
                  trailing: Text(block.timestamp.split('.').first),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// 8) Özet
class SummaryScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Akıllı Özet')),
        body: Center(child: Text('Mesajları AI ile otomatik özetleme buraya')),
      );
}

class GroupListPage extends StatelessWidget {
  final List<Map<String, dynamic>> mockGroups = [
    {
      'name': 'Mopple Fanları',
      'description': 'Mopple kullanıcıları burada!',
      'isPrivate': false,
    },
    {
      'name': 'Sosyal Proje',
      'description': 'Gizli tartışmalar burada',
      'isPrivate': true,
    }
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Gruplar")),
      body: ListView.builder(
        itemCount: mockGroups.length,
        itemBuilder: (context, index) {
          final group = mockGroups[index];
          return ListTile(
            title: Text(group['name']),
            subtitle: Text(group['description']),
            trailing: group['isPrivate'] ? Icon(Icons.lock) : Icon(Icons.lock_open),
            onTap: () {
              // TODO: Grup detayına git
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => GroupCreatePage()),
        ),
        child: Icon(Icons.add),
      ),
    );
  }
}

class MediaPickerScreen extends StatefulWidget {
  @override
  _MediaPickerScreenState createState() => _MediaPickerScreenState();
}

class _MediaPickerScreenState extends State<MediaPickerScreen> {
  final ImagePicker _picker = ImagePicker();
  XFile? _image;


  // Fotoğraf seçme fonksiyonu
  Future<void> _pickImage() async {
    final XFile? pickedFile = await _picker.pickImage(source: ImageSource.gallery);
    if (pickedFile != null) {
      setState(() {
        _image = pickedFile;
      });
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Medya Paylaş')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _image != null ? Image.file(File(_image!.path)) : Text('Henüz bir medya seçilmedi.'),
            ElevatedButton(
              onPressed: _pickImage,
              child: Text('Medya Seç'),
            ),
          ],
        ),
      ),
    );
  }
}

class GroupChatPage extends StatefulWidget {
  final String groupId;
  final String userId;

  const GroupChatPage({required this.groupId, required this.userId});


  @override
  State<GroupChatPage> createState() => _GroupChatPageState();
}

class _GroupChatPageState extends State<GroupChatPage> {
  final TextEditingController _controller = TextEditingController();
  final List<String> _messages = [];
  final ImagePicker _picker = ImagePicker();
  File? _selectedImage;
  String? _selectedVideo;


  @override
  void initState() {
    super.initState();
    SocketService().init(widget.groupId, widget.userId);
    SocketService().onMessage((data) {
      setState(() {
        // Gelen mesajı kontrol et ve uygun şekilde işle
        if (data['text'].startsWith("data:image")) {
          _messages.add("Resim: " + data['text']);
        } else if (data['text'].startsWith("data:video")) {
          _messages.add("Video: " + data['text']);
        } else {
          _messages.add(data['text']);
        }
      });
    });
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isNotEmpty) {
      SocketService().sendMessage(text);
      setState(() {
        _messages.add("Ben: $text");
      });
      _controller.clear();
    }
  }

  // Medya seçme işlemi
  Future<void> _pickMedia() async {
    final pickedFile = await _picker.pickImage(source: ImageSource.gallery);
    if (pickedFile != null) {
      setState(() {
        _selectedImage = File(pickedFile.path);
      });
      _sendImage(_selectedImage!);
    }
  }

  // Video seçme işlemi
  Future<void> _pickVideo() async {
    final pickedFile = await _picker.pickVideo(source: ImageSource.gallery);
    if (pickedFile != null) {
      setState(() {
        _selectedVideo = pickedFile.path;
      });
      _sendVideo(_selectedVideo!);
    }
  }


  // Resim olarak gönderme işlemi
  void _sendVideo(String videoPath) {
    final videoBytes = File(videoPath).readAsBytesSync();
    final base64Video = base64Encode(videoBytes);
    SocketService().sendMessage(base64Video);
    setState(() {
      _messages.add("Ben: Video gönderildi");
    });
}


  // Resim gönderme işlemi
  void _sendImage(File image) {
    final base64Image = base64Encode(image.readAsBytesSync());
    SocketService().sendMessage(base64Image); // Media message (image in base64)
    setState(() {
      _messages.add("Ben: Resim gönderildi!");
    });
  }

  @override
  void dispose() {
    SocketService().disconnect();
    super.dispose();
  }

  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Grup Mesajları')),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: EdgeInsets.all(8),
              children: _messages.map((msg) {
                if (msg.startsWith("Ben: Resim")) {
                  return Image.memory(base64Decode(msg.split(":")[1].trim()));
                } else if (msg.startsWith("Ben: Video")) {
                  return Text("Video gönderildi");
                } else {
                  return Text(msg);
                }
              }).toList(),
            ),
          ),
          Row(
            children: [
              Expanded(child: TextField(controller: _controller)),
              IconButton(icon: Icon(Icons.send), onPressed: _sendMessage),
              IconButton(icon: Icon(Icons.image), onPressed: _pickMedia), // Medya seçme butonu
              IconButton(icon: Icon(Icons.video_library), onPressed: _pickVideo), // Video seçme butonu
            ],
          ),
        ],
      ),
    );
  }
}

/// 9) Video Call
class VideoCallScreen extends StatefulWidget {
  const VideoCallScreen({Key? key}) : super(key: key);

  @override
  _VideoCallScreenState createState() => _VideoCallScreenState();
}

class _VideoCallScreenState extends State<VideoCallScreen> {
  final _localRenderer = RTCVideoRenderer();
  final _remoteRenderer = RTCVideoRenderer();
  bool _inCalling = false;

  @override
  void initState() {
    super.initState();
    initRenderers();
  }

  Future<void> initRenderers() async {
    await _localRenderer.initialize();
    await _remoteRenderer.initialize();
  }

  Future<void> startCall() async {
    final mediaConstraints = {'audio': true, 'video': {'facingMode': 'user'}};
    MediaStream stream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
    _localRenderer.srcObject = stream;
    _remoteRenderer.srcObject = stream;
    setState(() => _inCalling = true);
  }

  Future<void> endCall() async {
    _localRenderer.srcObject?.getTracks().forEach((t) => t.stop());
    _remoteRenderer.srcObject?.getTracks().forEach((t) => t.stop());
    setState(() => _inCalling = false);
  }

  @override
  void dispose() {
    _localRenderer.dispose();
    _remoteRenderer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Görüntülü Arama')),
        body: Column(children: [
          Expanded(child: RTCVideoView(_localRenderer, mirror: true)),
          Expanded(child: RTCVideoView(_remoteRenderer)),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            ElevatedButton(onPressed: _inCalling ? null : startCall, child: Text('Aramayı Başlat')),
            SizedBox(width: 20),
            ElevatedButton(onPressed: _inCalling ? endCall : null, child: Text('Bitir')),
          ])
        ]),
      );
}

class GroupDetailPage extends StatefulWidget {
  final String groupId;
  final String groupName;
  final String userId;

  const GroupDetailPage({required this.groupId, required this.groupName, required this.userId});

  @override
  State<GroupDetailPage> createState() => _GroupDetailPageState();
}

class _GroupDetailPageState extends State<GroupDetailPage> {
  bool isMember = false;

  void _toggleMembership() {
    setState(() {
      isMember = !isMember;
    });
  }

  void _openChat() {
    if (isMember) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => GroupChatPage(
            groupId: widget.groupId,
            userId: widget.userId,
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.groupName)),
      body: Column(
        children: [
          ListTile(
            title: Text('Grup: ${widget.groupName}'),
            subtitle: Text('Katılımcı: ??? kişi'),
          ),
          ElevatedButton(
            onPressed: _toggleMembership,
            child: Text(isMember ? 'Gruptan Ayrıl' : 'Gruba Katıl'),
          ),
          if (isMember)
            ElevatedButton.icon(
              onPressed: _openChat,
              icon: Icon(Icons.chat),
              label: Text('Sohbete Git'),
            ),
        ],
      ),
    );
  }
}

class FriendlyRequests extends StatefulWidget {
  @override
  _FriendlyRequestsState createState() => _FriendlyRequestsState();
}

class _FriendlyRequestsState extends State<FriendlyRequests> {
  List<String> users = [];

  void _getUser() {
    final requests = "You have a Friend Request by ${users.length + 1}, ${DateTime.now().hour}:${DateTime.now().second}";
    setState(() {
      users.add(requests);
    });
  }

  void refuseRequests() {
    setState(() {
      users.clear();
    });
  }

  void acceptRequests() {
    final text = "Accepted! Friend Request ${users.length}";
    setState(() {
      users.add(text);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Friends")),
      body: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              ElevatedButton(onPressed: _getUser, child: Text("New Request")),
              ElevatedButton(onPressed: acceptRequests, child: Text("Accept All")),
              ElevatedButton(onPressed: refuseRequests, child: Text("Refuse All")),
            ],
          ),
          Expanded(
            child: ListView.builder(
              itemCount: users.length,
              itemBuilder: (context, index) {
                return ListTile(
                  leading: Icon(Icons.person),
                  title: Text(users[index]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class MeshStubScreen extends StatefulWidget {
  @override
  _MeshStubScreenState createState() => _MeshStubScreenState();
}

class _MeshStubScreenState extends State<MeshStubScreen> {
  List<String> fakeDevices = [];

  void _scanDevices() {
    final newDevice = "Cihaz ${fakeDevices.length + 1} - ${DateTime.now().minute}:${DateTime.now().second}";
    setState(() {
      fakeDevices.add(newDevice);
    });
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Cihaz Adı - Mesh")),
      body: Column(
        children: [
          ElevatedButton(onPressed: _scanDevices, child: Text("Yeni Cihaz Tara")),
          Expanded(
            child: ListView.builder(
              itemCount: fakeDevices.length,
              itemBuilder: (context, index) {
                return ListTile(
                  leading: Icon(Icons.router),
                  title: Text(fakeDevices[index]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
