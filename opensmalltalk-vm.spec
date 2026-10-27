%global debugcflags -g
%global _disable_lto 1

Summary:	OpenSmalltalk Cog Spur virtual machine
Name:		opensmalltalk-vm
Version:	202606270913
Release:	1
License:	MIT
Group:		Development/Languages
Url:		https://opensmalltalk.org/
# https://github.com/OpenSmalltalk/opensmalltalk-vm/archive/refs/tags/202606270913.tar.gz
Source0:	%{name}-%{version}.tar.gz
Source1:	sqSCCSVersion.h
Source2:	plugins.ext
ExclusiveArch:	x86_64 znver1 aarch64
BuildRequires:	make
BuildRequires:	clang
BuildRequires:	gcc
BuildRequires:	gcc-c++
BuildRequires:	pkgconfig(alsa)
BuildRequires:	pkgconfig(libpulse)
BuildRequires:	pkgconfig(libpulse-simple)
BuildRequires:	pkgconfig(uuid)
BuildRequires:	pkgconfig(gl)
BuildRequires:	pkgconfig(x11)
BuildRequires:	pkgconfig(xext)
BuildRequires:	pkgconfig(xrender)
BuildRequires:	pkgconfig(xrandr)
BuildRequires:	pkgconfig(openssl)
BuildRequires:	pkgconfig(pangocairo)
BuildRequires:	pkgconfig(zlib)
# SqueakSSL dlopens OpenSSL instead of linking it.
Requires:	libssl.so.4()(64bit)
Requires:	libcrypto.so.4()(64bit)
# Display scaling dlopens Xrandr.
Requires:	libXrandr.so.2()(64bit)

%description
OpenSmalltalk is the Cog Spur virtual machine used by Squeak and other
Smalltalk systems. This is the production 64-bit VM, built from source,
with ALSA and PulseAudio for sound and X11 for display.

%prep
%setup -q
# GitHub archives do not expand the version keywords. Use the release header.
cp -f %{SOURCE1} platforms/Cross/vm/sqSCCSVersion.h
sed -i \
	-e 's|\$Rev\$|$Rev: %{version} $|g' \
	-e 's|\$URL\$|$URL: https://github.com/OpenSmalltalk/opensmalltalk-vm $|g' \
	platforms/Cross/plugins/sqPluginsSCCSVersion.h
# The wrapper makefile hardcodes lib/squeak. Plugins live in the real libdir.
sed -i 's|lib/squeak/|%{_lib}/squeak/|g' platforms/unix/config/Makefile.in
# zlib's search adds -L/usr/lib and never restores LDFLAGS, which then
# selects the 32-bit multilib libc and disables every later library test.
sed -i 's|-L${ZLIB_HOME}/lib|-L${ZLIB_HOME}/%{_lib}|g' platforms/unix/config/configure
# glibc declares login_tty in utmp.h. utmpx.h does not.
sed -i 's|<utmpx.h>|<utmp.h>|' platforms/unix/plugins/PseudoTTYPlugin/openpty.h
# dlopen the runtime soname. libXrandr.so is only in the devel package.
sed -i 's|"libXrandr\.so"|"libXrandr.so.2"|' platforms/unix/vm-display-X11/sqUnixX11Scale.c

%build
export LANG=C LC_ALL=C
# Plugin objects resolve VM symbols at dlopen, so --no-undefined must not
# be on the link line. -flto and -g3 also break this VM's build.
ldflags=$(echo "%{build_ldflags}" | sed -e 's/-Wl,--no-undefined//g' -e 's/-flto//g')
export LDFLAGS="$ldflags -L%{_libdir} -O2 -fno-lto -fno-omit-frame-pointer"
export LIBS="-lrt"
%ifarch aarch64
# Upstream builds ARM fast-bitblt with gcc. Clang miscompiles it.
export CC=gcc
export CXX=g++
# gcc 16 defaults to C23. PseudoTTYPlugin.h still uses empty parameter
# lists, which C23 reads as "no arguments".
export CFLAGS="%{optflags} -O2 -fno-lto -fno-omit-frame-pointer -Wno-error=format-security -DNDEBUG -DDEBUGVM=0 -DCOGMTVM=0 -D_GNU_SOURCE -march=armv8-a -mtune=cortex-a72 -DUSEEVDEV -DDUAL_MAPPED_CODE_ZONE=1 -std=gnu17"
%else
export CC=clang
export CXX=clang++
export CFLAGS="%{optflags} -O2 -fno-lto -fno-omit-frame-pointer -Wno-error=format-security -DNDEBUG -DDEBUGVM=0 -msse2 -DCOGMTVM=0 -D_GNU_SOURCE"
%endif
mkdir -p bld
cp -p building/linux64x64/squeak.cog.spur/plugins.int bld/plugins.int
cp -p %{SOURCE2} bld/plugins.ext
cd bld
# Use the shipped configure. Regenerating it would need libtoolize and
# would discard the zlib libdir edit above.
../platforms/unix/config/configure \
	--prefix=%{_prefix} \
	--bindir=%{_bindir} \
	--libdir=%{_libdir} \
	--mandir=%{_mandir} \
	--datadir=%{_datadir} \
	--without-npsqueak \
	--with-vmversion=5.0 \
	--with-src=src/spur64.cog \
	--with-scriptname=squeak \
	--x-includes=%{_includedir} \
	--x-libraries=%{_libdir} \
%ifarch aarch64
	--enable-fast-bitblt \
%else
	TARGET_ARCH="-m64" \
%endif
	CC="${CC}" \
	CXX="${CXX}" \
	CFLAGS="${CFLAGS}" \
	LIBS="${LIBS}" \
	LDFLAGS="${LDFLAGS}"
%make_build

%install
%make_build -C bld install-squeak install-plugins ROOT=%{buildroot}
# squeak.sh is installed at the prefix root. bin/squeak is the wrapper.
rm -f %{buildroot}%{_exec_prefix}/squeak
plugin=%{buildroot}%{_libdir}/squeak/7.0-%{version}-64bit
rm -f "$plugin"/vm-sound-NAS.so "$plugin"/vm-sound-sndio.so
test -f "$plugin"/squeak
test -f "$plugin"/vm-sound-ALSA.so
test -f "$plugin"/vm-sound-pulse.so
test -f "$plugin"/vm-display-X11.so
test -x %{buildroot}%{_bindir}/squeak

%check
ver=$("%{buildroot}%{_libdir}/squeak/7.0-%{version}-64bit/squeak" -version)
echo "$ver"
echo "$ver" | grep -F -q '%{version}'
echo "$ver" | grep -F -q 'Spur'
grep -F -q '%{_lib}/squeak/7.0-%{version}-64bit' %{buildroot}%{_bindir}/squeak

%files
%license LICENSE
%doc README.md
%{_bindir}/squeak
%{_libdir}/squeak
