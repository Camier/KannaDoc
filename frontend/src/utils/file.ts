export const getFileIcon = (fileType?: string) => {
  if (!fileType) return "📁";
  const type = fileType.split("/")[0];
  const subtype = fileType.split("/")[1];

  switch (type) {
    case "image":
      return "🖼️";
    case "application":
      switch (subtype) {
        case "pdf":
          return "📄";
        case "vnd.openxmlformats-officedocument.wordprocessingml.document":
          return "📝";
        case "vnd.ms-powerpoint":
        case "vnd.openxmlformats-officedocument.presentationml.presentation":
          return "📊";
        case "vnd.ms-excel":
        case "vnd.openxmlformats-officedocument.spreadsheetml.sheet":
          return "📈";
        default:
          return "📁";
      }
    default:
      return "📁";
  }
};

export const getFileExtension = (filename: string) => {
  return filename.split(".").pop()?.toLowerCase() || "";
};

export const base64Processor = {
  pattern: /data:image\/([a-z0-9+.-]+);base64,/gi,
  placeholder: "__BASE64_IMAGE_$1_PLACEHOLDER__",

  encode: function (str: string) {
    return str.replace(this.pattern, (match, subtype) => {
      return this.placeholder.replace("$1", subtype);
    });
  },

  decode: function (str: string) {
    // 分割占位符并转义静态部分
    const parts = this.placeholder.split(/\$1/g);
    const escapedParts = parts.map((part) =>
      part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    );
    // 拼接成完整正则表达式
    const regexStr = escapedParts.join("([a-z0-9+.-]+)");
    const reversePattern = new RegExp(regexStr, "gi");

    return str.replace(reversePattern, (full, subtype) => {
      return `data:image/${subtype};base64,`;
    });
  },
};

export const SupportUploadFormat = 
  ".odm,.sgl,.odt,.ott,.sxw,.stw,.fodt,.xml,.docx,.docm,.dotx,.dotm,.doc,.dot,.wps,.pdb,.pdf,.hwp,.html,.htm,.lwp,.psw,.rft,.sdw,.vor,.txt,.wpd,.oth,.ods,.ots,.sxc,.stc,.fods,.xml,.xlsx,.xlsm,.xltm,.xltx,.xlsb,.xls,.xlc,.xlm,.xlw,.xlk,.sdc,.vor,.dif,.wk1,.wks,.123,.pxl,.wb2,.csv,.odp,.otp,.sti,.sxd,.fodp,.xml,.pptx,.pptm,.ppsx,.potm,.potx,.ppt,.pps,.pot,.sdd,.vor,.sdp,.odg,.otg,.sxd,.std,.sgv,.sda,.vor,.sdd,.cdr,.svg,.vsd,.vst,.html,.htm,.stw,.sxg,.odf,.sxm,.smf,.mml,.odb";

  export const SupportFileFormat = 
  ["odm","sgl","odt","ott","sxw","stw","fodt","xml","docx","docm","dotx","dotm","doc","dot","wps","pdb","pdf","hwp","html","htm","lwp","psw","rft","sdw","vor","txt","wpd","oth","ods","ots","sxc","stc","fods","xml","xlsx","xlsm","xltm","xltx","xlsb","xls","xlc","xlm","xlw","xlk","sdc","vor","dif","wk1","wks","123","pxl","wb2","csv","odp","otp","sti","sxd","fodp","xml","pptx","pptm","ppsx","potm","potx","ppt","pps","pot","sdd","vor","sdp","odg","otg","sxd","std","sgv","sda","vor","sdd","cdr","svg","vsd","vst","html","htm","stw","sxg","odf","sxm","smf","mml","odb"]