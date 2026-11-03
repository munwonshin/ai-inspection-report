using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

[ComImport, Guid("000214F9-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAirShellLinkW {
 void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int count, IntPtr data, uint flags);
 void GetIDList(out IntPtr list);
 void SetIDList(IntPtr list);
 void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder text, int count);
 void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string text);
 void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int count);
 void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string path);
 void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder args, int count);
 void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string args);
 void GetHotkey(out short value);
 void SetHotkey(short value);
 void GetShowCmd(out int value);
 void SetShowCmd(int value);
 void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int count, out int index);
 void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string path, int index);
 void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, uint reserved);
 void Resolve(IntPtr window, uint flags);
 void SetPath([MarshalAs(UnmanagedType.LPWStr)] string path);
}
public static class AirInstallLink {
 static object Create() { return Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046"))); }
 public static void Save(string file, string target, string directory, string description) {
  object obj=Create();
  try {
   var link=(IAirShellLinkW)obj;
   link.SetPath(target); link.SetArguments(""); link.SetWorkingDirectory(directory);
   link.SetDescription(description); link.SetIconLocation(target,0); link.SetShowCmd(1);
   ((IPersistFile)obj).Save(file,true);
  } finally { Marshal.FinalReleaseComObject(obj); }
 }
 public static string Target(string file) {
  object obj=Create();
  try {
   ((IPersistFile)obj).Load(file,0);
   var path=new StringBuilder(32768);
   ((IAirShellLinkW)obj).GetPath(path,path.Capacity,IntPtr.Zero,4);
   return path.ToString();
  } finally { Marshal.FinalReleaseComObject(obj); }
 }
}
