{
  description = "hello world application using uv2nix";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    pyproject-nix,
    uv2nix,
    pyproject-build-systems,
    ...
  } @ inputs: let
    inherit (nixpkgs) lib;
    forAllSystems = lib.genAttrs lib.systems.flakeExposed;

    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};

    overlay = workspace.mkPyprojectOverlay {
      sourcePreference = "wheel";
    };

    editableOverlay = workspace.mkEditablePyprojectOverlay {
      root = "$REPO_ROOT";
    };

    pythonSets = forAllSystems (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
      in
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
        (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            overlay
          ]
        )
    );
  in {
    devShells = forAllSystems (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonSet = pythonSets.${system}.overrideScope editableOverlay;
        virtualenv = pythonSet.mkVirtualEnv "smtping-dev-env" workspace.deps.all;
      in {
        default = pkgs.mkShell {
          packages = [
            virtualenv
            pkgs.uv
            pkgs.swaks
          ];
          env = {
            UV_NO_SYNC = "1";
            UV_PYTHON = pythonSet.python.interpreter;
            UV_PYTHON_DOWNLOADS = "never";
          };
          shellHook = ''
            unset PYTHONPATH
            export REPO_ROOT=$(git rev-parse --show-toplevel)
          '';
        };
      }
    );

    packages = forAllSystems (system: {
      default = pythonSets.${system}.mkVirtualEnv "smtping-env" workspace.deps.default;
    });

    checks = let
      system = "x86_64-linux";
      pkgs = inputs.nixpkgs.legacyPackages."x86_64-linux";
    in {
      "x86_64-linux".default = pkgs.testers.runNixOSTest {
        name = "smtping-test";
        nodes = {
          machine = {pkgs, ...}: {
            imports = [inputs.self.nixosModules.default];
            environment.systemPackages = [pkgs.swaks];
            services.smtping.enable = true;
          };
        };
        testScript = ''
          start_all()

          # wait for socket service
          machine.wait_for_unit("smtping.socket")

          # wait for port to be open
          machine.wait_for_open_port(25)

          # wait for service to start
          machine.wait_for_unit("smtping.service")

          # Try an smtp session to the service
          status = machine.succeed("swaks -s localhost:25 -t test@test.test --quit-after rcpt")

          # Check if our server returns something.
          assert "250 OK" in status, f"'{status}' is not healthy! Check failed."
        '';
      };
    };

    nixosModules = {
      default = {
        config,
        lib,
        pkgs,
        ...
      }: let
        cfg = config.services.smtping;
        inherit (lib.options) mkOption;
        inherit (lib.modules) mkIf;
      in {
        options.services.smtping = {
          enable = mkOption {
            type = lib.types.bool;
            default = false;
            description = ''
              Enable SMTPing service
            '';
          };
          port = mkOption {
            type = lib.types.int;
            default = 25;
            description = ''
              Port to bind the SMTPing service to
            '';
          };
        };
        config = mkIf cfg.enable rec {
          users.extraGroups.smtping = {};
          users.extraUsers.smtping = {
            description = "smtping";
            group = "smtping";
            isSystemUser = true;
            useDefaultShell = true;
          };
          systemd.sockets.smtping = {
            description = "SMTPing Socket";
            wantedBy = ["sockets.target"];
            socketConfig = {
              ListenStream = ["${toString cfg.port}"];
              SocketMode = "0600";
              FileDescriptorName = "smtping";
              Service = "smtping.service";
            };
            partOf = ["smtping.service"];
          };
          systemd.services.smtping = {
            description = "SMTPing Service";
            after = ["network.target"];
            wantedBy = ["multi-user.target"];
            serviceConfig = {
              User = "smtping";
              Group = "smtping";
              ExecStart = "${self.packages.${pkgs.system}.default}/bin/smtping";
              Restart = "on-failure";
              AmbientCapabilities = "CAP_NET_BIND_SERVICE";
            };
          };
        };
      };
    };
  };
}
